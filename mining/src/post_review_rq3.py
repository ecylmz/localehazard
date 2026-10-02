"""Post-review RQ3 analyses (requested by the simulated reviewers; all labelled POST_REVIEW in the manuscript)."""
import csv, gzip, json, math, pathlib, re, collections, datetime, statistics, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from analyze_mining import boot_share
from analyze_validation import wilson
from classify_diffs import TEST_PATH

P = ROOT / "data/processed"
commits = {r["sha"]: r for r in csv.DictReader(open(P / "commits_classified.csv"))}
lin = list(csv.DictReader(open(P / "commits_lineages.csv")))
reps = [commits[r["sha"]] for r in lin if r["lineage_representative"] == "1"]
included = {r["sha"] for r in lin}
edits = collections.defaultdict(list)
for e in csv.DictReader(open(P / "repair_edits.csv")):
    edits[e["sha"]].append(e)
repo = lambda c: c["repo"].lower()
dirs = lambda c: sorted({e["direction"] for e in edits[c["sha"]]})
qset = lambda c: set(c["queries"].split(";"))
out = {}

# 1. validation re-based on v2 inclusion
key = {r["item_id"]: r for r in csv.DictReader(open(ROOT / "validation/sample_key.csv"))}
adj = {r["item_id"]: r for r in csv.DictReader(open(ROOT / "validation/adjudicated.csv"))}
inc_items = [i for i in key if key[i]["sample"] == "included"]
still = [i for i in inc_items if key[i]["sha"] in included]
dropped = [i for i in inc_items if key[i]["sha"] not in included]
g = [i for i in still if adj[i]["genuine"] == "YES"]
out["trigger_v2"] = dict(collections.Counter(adj[i]["trigger"] for i in g))
out["role_v2"] = dict(collections.Counter(adj[i]["role"] for i in g))
out["precision_v2"] = {"n": len(still), "k": len(g), "share": round(len(g) / len(still), 4), "wilson95": wilson(len(g), len(still)),
                       "dropped_by_v2": len(dropped), "dropped_genuine": sum(adj[i]["genuine"] == "YES" for i in dropped)}
exc_items = [i for i in key if key[i]["sample"] == "excluded"]
neg_k = sum(adj[i]["genuine"] == "YES" for i in exc_items)

# 2. recall estimate in the Turkic-query sub-frame
T = {"T1", "T2", "T3", "T4", "T5"}
fetched_T = [c for c in commits.values() if c["fetch_status"] == "200" and qset(c) & T]
inc_T = sum(1 for c in fetched_T if c["sha"] in included)
exc_T = sum(1 for c in fetched_T if c["sha"] not in included and c.get("format_only") == "0")
pr, (pl, ph) = out["precision_v2"]["share"], out["precision_v2"]["wilson95"]
ns, (nl, nh) = neg_k / len(exc_items), wilson(neg_k, len(exc_items))
rec = lambda p, n: inc_T * p / (inc_T * p + exc_T * n)
out["recall_turkic_subframe"] = {"included": inc_T, "excluded_nonformat": exc_T, "neg_genuine": f"{neg_k}/{len(exc_items)}",
                                 "estimate": round(rec(pr, ns), 3), "bounds": [round(rec(pl, nh), 3), round(rec(ph, nl), 3)]}

# 3. features by query family (excluding the queries that select on the feature)
A = {"A1", "A2", "A3", "A4", "A5"}
out["turkic_share_excluding_T_queries"] = boot_share([c for c in reps if not qset(c) & T], lambda c: c["msg_turkic"] == "1", repo)
out["analyzer_share_excluding_A_queries"] = boot_share([c for c in reps if not qset(c) & A], lambda c: c["msg_analyzer"] == "1", repo)
out["pinning_only_excluding_pinning_queries"] = boot_share([c for c in reps if not qset(c) <= {"J1", "J2", "J3", "J4", "J5", "N1", "N2", "N3", "N4", "C1", "C2", "C3", "S2"}], lambda c: dirs(c) == ["MACHINE_PINNING"], repo)

# 4. locale-relevant test changes
# Turkish letters outside the case-insensitive group: under re.I Python treats U+0130/U+0131 as variants of i.
LOCTEST = re.compile(r"(?i:tr[-_]TR|\"tr\"|'tr'|Locale\.setDefault|new Locale\(\s*\"tr|forLanguageTag\(\s*\"tr|CultureInfo\(\s*\"tr|Turkish|Turkey|LC_ALL|LC_CTYPE|LANG=|dotless|az[-_]AZ|lt[-_]LT)|[\u0130\u0131\u015e\u015f\u011e\u011f]")
loc_test = {}
for c in reps:
    d = json.load(gzip.open(ROOT / f"data/raw/commits/{c['sha']}.json.gz", "rt"))
    hit = False
    for f in d.get("files", []):
        if TEST_PATH.search(f["filename"]):
            for l in (f.get("patch") or "").split("\n"):
                if l.startswith("+") and not l.startswith("+++") and LOCTEST.search(l):
                    hit = True; break
        if hit: break
    loc_test[c["sha"]] = hit
out["locale_relevant_test"] = boot_share(reps, lambda c: loc_test[c["sha"]], repo)
out["locale_relevant_test_turkic_msg"] = boot_share([c for c in reps if c["msg_turkic"] == "1"], lambda c: loc_test[c["sha"]], repo)

# 5. agent comparison with a contemporaneous comparator and commit size
recent = [c for c in reps if (c["committer_date"] or "") >= "2025"]
ag = [c for c in recent if c.get("msg_ai_agent") == "1"]; nag = [c for c in recent if c.get("msg_ai_agent") != "1"]
nf = lambda cs: statistics.median(int(c["n_files"] or 0) for c in cs)
out["agents"] = {"agent_test": boot_share(ag, lambda c: c["test_change"] == "1", repo), "nonagent_2025_26_test": boot_share(nag, lambda c: c["test_change"] == "1", repo),
                 "agent_loctest": boot_share(ag, lambda c: loc_test[c["sha"]], repo), "nonagent_2025_26_loctest": boot_share(nag, lambda c: loc_test[c["sha"]], repo),
                 "median_files_agent": nf(ag), "median_files_nonagent_2025_26": nf(nag),
                 "fetched_2026_share": round(sum(1 for c in commits.values() if (c.get("committer_date") or "")[:4] == "2026") / len(commits), 3)}

# 6. multi-lineage repositories: same-day
byr = collections.defaultdict(list)
for c in reps:
    if c["committer_date"]:
        byr[repo(c)].append(datetime.datetime.fromisoformat(c["committer_date"].replace("Z", "+00:00")))
multi = {r: sorted(v) for r, v in byr.items() if len(v) >= 2}
out["multi_repos"] = {"n": len(multi), "within_1_day": sum(1 for v in multi.values() if (v[-1] - v[0]).days < 1),
                      "within_7_days": sum(1 for v in multi.values() if (v[-1] - v[0]).days < 7)}

# 7. role consistency in the coded sample (v1 sample, restricted to v2-included genuine items)
cons = collections.Counter()
for i in g:
    sha = key[i]["sha"]; ds = sorted({e["direction"] for e in edits[sha]}); role = adj[i]["role"]
    if ds == ["MACHINE_PINNING"]:
        cons["pinning_on_" + role] += 1
    elif ds == ["LINGUISTIC_REPAIR"]:
        cons["towards_aware_on_" + role] += 1
    else:
        cons["both_directions_" + role] += 1
out["role_consistency_coded"] = dict(cons)
k_inc = cons["pinning_on_LINGUISTIC"] + cons["towards_aware_on_MACHINE"]
k_mix = cons["pinning_on_MIXED"] + cons["towards_aware_on_MIXED"]
k_cons = cons["pinning_on_MACHINE"] + cons["towards_aware_on_LINGUISTIC"]
out["role_consistency_summary"] = {"n": len(g), "consistent": k_cons, "introduces_cdm": k_inc, "mixed": k_mix,
                                   "unclear_or_other": len(g) - k_cons - k_inc - k_mix,
                                   "pinning_total": sum(v for k, v in cons.items() if k.startswith("pinning_on_")),
                                   "pinning_on_linguistic_or_mixed": cons["pinning_on_LINGUISTIC"] + cons["pinning_on_MIXED"],
                                   "introduces_wilson": wilson(k_inc, len(g))}

# 8. linguistic-direction items: target locale of the 40 machine/mixed locale-aware changes
G = {r["item_id"]: {k: (r[k] or "").strip().upper() for k in ("role", "change")} for r in csv.DictReader(open(ROOT / "validation/ling/coder_A.csv"))}
GB = {r["item_id"]: {k: (r[k] or "").strip().upper() for k in ("role", "change")} for r in csv.DictReader(open(ROOT / "validation/ling/coder_B.csv"))}
fin = {i: G[i] for i in G if G[i] == GB[i]}
fin.update({r["item_id"]: {k: (r[k] or "").strip().upper() for k in ("role", "change")} for r in csv.DictReader(open(ROOT / "validation/ling/adjudicated_disagreements.csv"))})
items = {json.loads(l)["item_id"]: json.loads(l) for l in open(ROOT / "validation/ling/items.jsonl")}
lkey = {r["item_id"]: r["sha"] for r in csv.DictReader(open(ROOT / "validation/ling/key.csv"))}
def target(it):
    add = " ".join(x["added"] for x in it["changed_lines"])
    if re.search(r"toLocale(Lower|Upper)Case\(\s*\)", add): return "no_argument_default"
    if re.search(r"toLocale(Lower|Upper)Case\(\s*['\"](tr|az|lt)", add, re.I) or re.search(r"forLanguageTag\(\"(tr|az|lt)", add): return "explicit_turkic"
    if re.search(r"toLocale(Lower|Upper)Case\(\s*\[?\s*['\"]en", add) or re.search(r"Locale\.(ENGLISH|US)\b", add): return "explicit_english"
    if re.search(r"toLocale(Lower|Upper)Case\(\s*['\"]", add): return "explicit_other_fixed"
    return "variable_or_culture_parameter"
la = [i for i in fin if fin[i]["change"] == "LOCALE_AWARE" and fin[i]["role"] in ("MACHINE", "MIXED")]
eco = lambda i: sorted({e["ecosystem"] for e in edits.get(lkey[i], [])}) or ["(dropped by v2)"]
out["towards_aware_machine_items"] = {"n": len(la), "still_included_v2": sum(1 for i in la if lkey[i] in included),
                                      "target": dict(collections.Counter(target(items[i]) for i in la)),
                                      "ecosystem": dict(collections.Counter(";".join(eco(i)) for i in la)),
                                      "js_no_argument": sum(1 for i in la if target(items[i]) == "no_argument_default" and "js" in eco(i))}
mach_only = [i for i in la if fin[i]["role"] == "MACHINE"]
n_aware = sum(1 for i in fin if fin[i]["change"] == "LOCALE_AWARE")
out["towards_aware_machine_only"] = {"k": len(mach_only), "n": n_aware, "share": round(len(mach_only) / n_aware, 4), "wilson95": wilson(len(mach_only), n_aware),
    "mixed": len(la) - len(mach_only), "no_argument": sum(1 for i in mach_only if target(items[i]) == "no_argument_default"),
    "english": sum(1 for i in mach_only if target(items[i]) == "explicit_english"),
    "realised_any_input": sum(1 for i in mach_only if target(items[i]) not in ("no_argument_default", "explicit_english"))}
import classify_diffs as _cd
out["rule_directions"] = dict(collections.Counter(r[2] for r in _cd.RULES))
realised = [i for i in la if target(items[i]) not in ("explicit_english",)]
out["towards_aware_machine_items"]["excluding_explicit_english"] = len(realised)

# 9. precision by stratum (coded sample, v2-included)
strat = collections.defaultdict(lambda: [0, 0])
for i in still:
    sha = key[i]["sha"]; eco_ = sorted({e["ecosystem"] for e in edits[sha]}); op = sorted({e["op"] for e in edits[sha]})
    k = f"{';'.join(eco_)}|{';'.join(op)}"; strat[k][1] += 1; strat[k][0] += adj[i]["genuine"] == "YES"
out["precision_by_stratum"] = {k: f"{v[0]}/{v[1]}" for k, v in sorted(strat.items(), key=lambda kv: -kv[1][1])}

# 10. lineage sensitivity: fingerprint within repository
fp = collections.Counter()
for c in (commits[s] for s in included):
    fp[(repo(c), tuple(sorted(e["removed"] + "→" + e["added"] for e in edits[c["sha"]])))] += 1
out["lineages_if_fingerprint_within_repo"] = len(fp)

json.dump(out, open(ROOT / "results/rq3_post_review.json", "w"), indent=1)
print(json.dumps(out, indent=1))
