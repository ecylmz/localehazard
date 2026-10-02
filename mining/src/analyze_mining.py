"""RQ3 aggregate analysis: funnel, lineage deduplication, repository-clustered bootstrap intervals."""
import csv, json, pathlib, random, re, statistics, collections, datetime

ROOT = pathlib.Path(__file__).resolve().parents[1]
P = ROOT / "data/processed"
VENDORED = re.compile(r"(^|/)(vendor|third_party|thirdparty|external|node_modules|deps|dist|bin|obj|build|out)/|\.min\.js$|\.bundle\.js$", re.I)  # v2 adds generated output
B = 2000
rng = random.Random(20261003)


def load():
    commits = list(csv.DictReader(open(P / "commits_classified.csv")))
    edits = list(csv.DictReader(open(P / "repair_edits.csv")))
    return commits, edits


def boot_share(units, pred, cluster):
    """Share of units satisfying pred with a percentile bootstrap that resamples repositories."""
    by = collections.defaultdict(list)
    for u in units:
        by[cluster(u)].append(u)
    keys = list(by)
    est = sum(1 for u in units if pred(u)) / len(units)
    reps = []
    for _ in range(B):
        s = [rng.choice(keys) for _ in keys]
        n = sum(len(by[k]) for k in s)
        reps.append(sum(1 for k in s for u in by[k] if pred(u)) / n)
    reps.sort()
    return {"k": sum(1 for u in units if pred(u)), "n": len(units), "share": round(est, 4),
            "ci95": [round(reps[int(0.025 * B)], 4), round(reps[int(0.975 * B) - 1], 4)]}


def main():
    commits, edits = load()
    import sys as _sys; _sys.path.insert(0, str(ROOT / "src"))
    from fetch_details import iter_search_rows
    search_rows = sum(1 for _ in iter_search_rows())
    meta = {f.stem.split(".")[0]: json.load(open(f)) for f in (ROOT / "data/raw/search").glob("*.meta.json")}
    fetched = [c for c in commits if c["fetch_status"] == "200"]
    # vendored exclusion at edit level
    edits_nv = [e for e in edits if not VENDORED.search(e["file"])]
    by_sha = collections.defaultdict(list)
    for e in edits_nv:
        by_sha[e["sha"]].append(e)
    inc = [c for c in fetched if c["sha"] in by_sha]
    # lineage: same edit fingerprint (recomputed on non-vendored edits) -> earliest commit
    def fp(sha):
        return tuple(sorted(e["removed"] + "→" + e["added"] for e in by_sha[sha]))
    groups = collections.defaultdict(list)
    for c in inc:
        groups[fp(c["sha"])].append(c)
    reps = []
    lin_rows = []
    for g in groups.values():
        g.sort(key=lambda c: (c["committer_date"] or "", c["sha"]))
        reps.append(g[0])
        for i, c in enumerate(g):
            lin_rows.append({"sha": c["sha"], "repo": c["repo"], "lineage": g[0]["sha"], "lineage_size": len(g),
                             "lineage_representative": int(i == 0)})
    with open(P / "commits_lineages.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(lin_rows[0])); w.writeheader(); w.writerows(lin_rows)
    rep_shas = {c["sha"] for c in reps}
    E = [e for e in edits_nv if e["sha"] in rep_shas]
    # per-commit derived
    def ecos(c): return sorted({e["ecosystem"] for e in by_sha[c["sha"]]})
    def ops(c): return sorted({e["op"] for e in by_sha[c["sha"]]})
    def dirs(c): return sorted({e["direction"] for e in by_sha[c["sha"]]})
    repo = lambda c: c["repo"].lower()
    eco_c = collections.Counter(x for c in reps for x in ecos(c))
    op_c = collections.Counter(x for c in reps for x in ops(c))
    dir_c = collections.Counter("+".join(dirs(c)) for c in reps)
    eco_op = collections.Counter((e["ecosystem"], e["op"]) for e in E)
    eco_op_commits = collections.Counter((x, y) for c in reps for x in ecos(c) for y in ops(c))
    sites = [len(by_sha[c["sha"]]) for c in reps]
    repos = collections.Counter(repo(c) for c in reps)
    multi = {r: n for r, n in repos.items() if n >= 2}
    gaps = []
    for r in multi:
        ds = sorted(datetime.datetime.fromisoformat(c["committer_date"].replace("Z", "+00:00")) for c in reps if repo(c) == r and c["committer_date"])
        if len(ds) >= 2:
            gaps.append((ds[-1] - ds[0]).days)
    stars = lambda c: int(c["stars"]) if c.get("stars") not in (None, "", "None") else -1
    year = collections.Counter((c["committer_date"] or "")[:4] for c in reps)
    out = {
        "funnel": {"queries": len(meta), "search_hits": search_rows,
                   "reported_total_counts": {k: v["total_count"] for k, v in sorted(meta.items())},
                   "unique_nonmerge_commits": len(commits), "fetched_ok": len(fetched),
                   "with_in_scope_edit_before_vendored_exclusion": sum(1 for c in fetched if c["included"] == "1"),
                   "format_only": sum(1 for c in fetched if c["format_only"] == "1"),
                   "included_after_vendored_exclusion": len(inc), "lineages": len(reps),
                   "commits_collapsed_by_lineage": len(inc) - len(reps), "repositories": len(repos),
                   "repair_edits_in_lineages": len(E)},
        "ecosystem_commits": dict(eco_c.most_common()), "op_commits": dict(op_c.most_common()),
        "direction_commits": dict(dir_c.most_common()),
        "eco_op_commits": {f"{a}|{b}": n for (a, b), n in eco_op_commits.most_common()},
        "eco_op_edits": {f"{a}|{b}": n for (a, b), n in eco_op.most_common()},
        "sites_per_commit": {"median": statistics.median(sites), "mean": round(statistics.mean(sites), 2),
                             "p90": sorted(sites)[int(0.9 * len(sites))], "max": max(sites), "single_site_share": round(sum(1 for s in sites if s == 1) / len(sites), 4)},
        "repos_with_multiple_lineages": len(multi), "repos_total": len(repos),
        "multi_lineage_repo_share": round(len(multi) / len(repos), 4),
        "lineages_in_multi_repos": sum(multi.values()),
        "gap_days_multi_repos": {"median": statistics.median(gaps) if gaps else None, "n": len(gaps)},
        "shares": {
            "test_change": boot_share(reps, lambda c: c["test_change"] == "1", repo),
            "msg_turkic": boot_share(reps, lambda c: c["msg_turkic"] == "1", repo),
            "msg_failure": boot_share(reps, lambda c: c["msg_failure"] == "1", repo),
            "msg_analyzer": boot_share(reps, lambda c: c["msg_analyzer"] == "1", repo),
            "msg_issue_ref": boot_share(reps, lambda c: c["msg_issue_ref"] == "1", repo),
            "msg_bot": boot_share(reps, lambda c: c["msg_bot"] == "1", repo),
            "machine_pinning_only": boot_share(reps, lambda c: dirs(c) == ["MACHINE_PINNING"], repo),
            "any_linguistic_repair": boot_share(reps, lambda c: "LINGUISTIC_REPAIR" in dirs(c), repo),
            "turkic_and_test": boot_share(reps, lambda c: c["msg_turkic"] == "1" and c["test_change"] == "1", repo),
        },
        "shares_turkic_subset": {
            "test_change": boot_share([c for c in reps if c["msg_turkic"] == "1"], lambda c: c["test_change"] == "1", repo),
        } if any(c["msg_turkic"] == "1" for c in reps) else {},
        "stars_ge_10": {"lineages": sum(1 for c in reps if stars(c) >= 10),
                        "repos": len({repo(c) for c in reps if stars(c) >= 10}),
                        "test_change": boot_share([c for c in reps if stars(c) >= 10], lambda c: c["test_change"] == "1", repo) if any(stars(c) >= 10 for c in reps) else None,
                        "msg_turkic": boot_share([c for c in reps if stars(c) >= 10], lambda c: c["msg_turkic"] == "1", repo) if any(stars(c) >= 10 for c in reps) else None},
        "year_lineages": dict(sorted(year.items())),
        "post_hoc_ai_agent": {
            "lineages_with_trailer": boot_share(reps, lambda c: c.get("msg_ai_agent") == "1", repo),
            "by_year": {y: sum(1 for c in reps if (c["committer_date"] or "")[:4] == y and c.get("msg_ai_agent") == "1") for y in sorted(year)},
            "without_trailer": {k: boot_share([c for c in reps if c.get("msg_ai_agent") != "1"], f, repo) for k, f in (
                ("test_change", lambda c: c["test_change"] == "1"), ("msg_turkic", lambda c: c["msg_turkic"] == "1"),
                ("machine_pinning_only", lambda c: dirs(c) == ["MACHINE_PINNING"]), ("msg_failure", lambda c: c["msg_failure"] == "1"))},
            "with_trailer_test_change": boot_share([c for c in reps if c.get("msg_ai_agent") == "1"], lambda c: c["test_change"] == "1", repo),
            "before_2025": {k: boot_share([c for c in reps if (c["committer_date"] or "") < "2025"], f, repo) for k, f in (
                ("test_change", lambda c: c["test_change"] == "1"), ("msg_turkic", lambda c: c["msg_turkic"] == "1"),
                ("machine_pinning_only", lambda c: dirs(c) == ["MACHINE_PINNING"]))},
        },
    }
    (ROOT / "results").mkdir(exist_ok=True)
    json.dump(out, open(ROOT / "results/rq3_mining.json", "w"), indent=1)
    print(json.dumps({k: out[k] for k in ("funnel", "ecosystem_commits", "op_commits", "direction_commits", "sites_per_commit")}, indent=1))
    print(json.dumps(out["shares"], indent=1))


if __name__ == "__main__":
    main()
