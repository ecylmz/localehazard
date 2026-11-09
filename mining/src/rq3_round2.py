"""Regenerate results/rq3_round2.json (round 4; the file of 2026-10-02 had no script in the package).

non_same_day_multi:        repositories with two or more lineages whose first and last lineage are at least one day
                           apart (src/post_review_rq3.py section 6 counts the others as within_1_day);
median_gap_non_same_day:   median days between the first and last lineage of those repositories;
agent_test_diff:           share of lineages with a coding-agent trailer that touch a test file minus the share among
                           contemporaneous lineages without a trailer (committer date 2025 or later, as in
                           post_review_rq3.py section 5), with a percentile bootstrap that resamples repositories
                           within each group (2,000 replicates).
Usage: python3 src/rq3_round2.py [--seed N] [--print-only]
"""
import argparse, csv, datetime, json, pathlib, random, statistics, collections

ROOT = pathlib.Path(__file__).resolve().parents[1]
ap = argparse.ArgumentParser(); ap.add_argument("--seed", type=int, default=20261003); ap.add_argument("--print-only", action="store_true")
args = ap.parse_args()
P = ROOT / "data/processed"
commits = {r["sha"]: r for r in csv.DictReader(open(P / "commits_classified.csv"))}
reps = [commits[r["sha"]] for r in csv.DictReader(open(P / "commits_lineages.csv")) if r["lineage_representative"] == "1"]
repo = lambda c: c["repo"].lower()

byr = collections.defaultdict(list)
for c in reps:
    if c["committer_date"]:
        byr[repo(c)].append(datetime.datetime.fromisoformat(c["committer_date"].replace("Z", "+00:00")))
multi = {r: sorted(v) for r, v in byr.items() if len(v) >= 2}
other = [v for v in multi.values() if (v[-1] - v[0]).days >= 1]

recent = [c for c in reps if (c["committer_date"] or "") >= "2025"]
ag = [c for c in recent if c.get("msg_ai_agent") == "1"]; nag = [c for c in recent if c.get("msg_ai_agent") != "1"]
share = lambda cs: sum(1 for c in cs if c["test_change"] == "1") / len(cs)
rng = random.Random(args.seed); B = 2000


def clusters(cs):
    by = collections.defaultdict(list)
    for c in cs:
        by[repo(c)].append(c)
    return list(by.values())


ca, cn = clusters(ag), clusters(nag)
reps_d = sorted(share([c for g in (rng.choice(ca) for _ in ca) for c in g]) - share([c for g in (rng.choice(cn) for _ in cn) for c in g]) for _ in range(B))
out = {"non_same_day_multi": len(other), "median_gap_non_same_day": statistics.median((v[-1] - v[0]).days for v in other),
       "agent_test_diff": [round(share(ag) - share(nag), 4), round(reps_d[int(0.025 * B)], 4), round(reps_d[int(0.975 * B) - 1], 4)]}
if not args.print_only:
    json.dump(out, open(ROOT / "results/rq3_round2.json", "w"))
print(json.dumps(out))
