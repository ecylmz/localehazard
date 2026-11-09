"""Round-4 reference rate analysis (protocol/DEVIATIONS.md, 2026-11-09).

Compares, within the same repositories, the year-anchor lineage representative (the earliest representative repair
of each repository, as used by src/r4_reference_commits.py) with the reference commits drawn from that repository
and year: share touching a test file (TEST_PATH) and share adding a locale-test line (LOCTEST).
Repository is the unit: per repository, repair value (0/1) minus the mean over its fetched reference commits.
Intervals: percentile bootstrap over repositories (2,000 replicates, seed 20261109).
Writes results/r4_reference.json.
"""
import csv, json, pathlib, random, collections

ROOT = pathlib.Path(__file__).resolve().parents[1]
P = ROOT / "data/processed"
rng = random.Random(20261109); B = 2000

commits = {r["sha"]: r for r in csv.DictReader(open(P / "commits_classified.csv"))}
loc = {r["sha"]: r for r in csv.DictReader(open(P / "locale_test_indicators.csv"))}
anchor = {}
for r in csv.DictReader(open(P / "commits_lineages.csv")):
    if r["lineage_representative"] != "1":
        continue
    c = commits[r["sha"]]; d = c["committer_date"] or ""
    k = c["repo"].lower()
    if d and (k not in anchor or d < commits[anchor[k]]["committer_date"]):
        anchor[k] = r["sha"]
ref = collections.defaultdict(list)
fail = collections.Counter()
for r in csv.DictReader(open(P / "reference_commits.csv")):
    if r["status"] == "200":
        ref[r["repo"].lower()].append((int(r["test_change"]), int(r["locale_test_line"])))
    else:
        fail[r["status"] or "none"] += 1
units = [(int(loc[anchor[k]]["test_change"]), int(loc[anchor[k]]["locale_test_line"]),
          sum(t for t, _ in v) / len(v), sum(l for _, l in v) / len(v)) for k, v in ref.items() if k in anchor]


def stat(us):
    n = len(us)
    return {"repair_test": sum(u[0] for u in us) / n, "reference_test": sum(u[2] for u in us) / n,
            "repair_loctest": sum(u[1] for u in us) / n, "reference_loctest": sum(u[3] for u in us) / n,
            "diff_test": sum(u[0] - u[2] for u in us) / n, "diff_loctest": sum(u[1] - u[3] for u in us) / n}


est = stat(units)
reps = [stat([rng.choice(units) for _ in units]) for _ in range(B)]
ci = {k: [round(sorted(r[k] for r in reps)[int(0.025 * B)], 4), round(sorted(r[k] for r in reps)[int(0.975 * B) - 1], 4)] for k in est}
out = {"repositories_with_reference": len(units), "repositories_planned": len(anchor),
       "reference_commits": sum(len(v) for v in ref.values()), "failures": dict(fail),
       "estimates": {k: round(v, 4) for k, v in est.items()}, "ci95": ci}
json.dump(out, open(ROOT / "results/r4_reference.json", "w"), indent=1)
print(json.dumps(out, indent=1))
