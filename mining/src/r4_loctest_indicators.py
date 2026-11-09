"""Round-4: per-lineage locale-test indicator, its matched added lines, and the Set-3 validation sample.

The indicator is the measure of src/post_review_rq3.py section 4, copied verbatim (TEST_PATH from classify_diffs.py,
LOCTEST below): a representative commit adds, in a file that matches TEST_PATH, a line that matches LOCTEST.
Needs the raw commit patches in data/raw/commits/ (not redistributed). Writes
  data/processed/locale_test_indicators.csv  (deposited, so the 7.6% can be recomputed without patches)
  validation/human_r4/set3_sample.csv         (50 positive, 40 negative with a test-file change, 10 negative
                                               without; seed 20261109; protocol/DEVIATIONS.md 2026-11-09)
  validation/human_r4/set3_items.jsonl        (what the coders see; no indicator value)
"""
import csv, gzip, json, pathlib, random, re, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from classify_diffs import TEST_PATH

LOCTEST = re.compile(r"(?i:tr[-_]TR|\"tr\"|'tr'|Locale\.setDefault|new Locale\(\s*\"tr|forLanguageTag\(\s*\"tr|CultureInfo\(\s*\"tr|Turkish|Turkey|LC_ALL|LC_CTYPE|LANG=|dotless|az[-_]AZ|lt[-_]LT)|[İıŞşĞğ]")
P = ROOT / "data/processed"
commits = {r["sha"]: r for r in csv.DictReader(open(P / "commits_classified.csv"))}
reps = [commits[r["sha"]] for r in csv.DictReader(open(P / "commits_lineages.csv")) if r["lineage_representative"] == "1"]

rows, details = [], {}
for c in reps:
    d = json.load(gzip.open(ROOT / f"data/raw/commits/{c['sha']}.json.gz", "rt"))
    files = d.get("files", [])
    tfiles = [f for f in files if TEST_PATH.search(f["filename"])]
    matched, test_added = [], []
    for f in tfiles:
        adds = [l[1:] for l in (f.get("patch") or "").split("\n") if l.startswith("+") and not l.startswith("+++")]
        test_added.append({"file": f["filename"], "added": adds})
        matched += [f"{f['filename']}: {l.strip()[:300]}" for l in adds if LOCTEST.search("+" + l)]
    rows.append({"sha": c["sha"], "repo": c["repo"], "test_change": c["test_change"], "test_files": len(tfiles),
                 "locale_test_line": int(bool(matched)), "n_matched_lines": len(matched), "matched_lines": " | ".join(matched[:5])})
    details[c["sha"]] = {"message": d.get("commit", {}).get("message", "") or c.get("message", ""), "files": [f["filename"] for f in files],
                         "test_added": test_added,
                         "patch": "\n".join(f"--- {f['filename']}\n{f.get('patch') or ''}" for f in files)}

k = sum(r["locale_test_line"] for r in rows)
ref = json.load(open(ROOT / "results/rq3_post_review.json"))["locale_relevant_test"]
assert (k, len(rows)) == (ref["k"], ref["n"]), (k, len(rows), ref)
assert all(r["test_change"] == "1" for r in rows if r["locale_test_line"]), "locale-test lineages must touch a test file"
with open(P / "locale_test_indicators.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

rng = random.Random(20261109)
pos = sorted(r["sha"] for r in rows if r["locale_test_line"])
neg_t = sorted(r["sha"] for r in rows if not r["locale_test_line"] and r["test_change"] == "1")
neg_n = sorted(r["sha"] for r in rows if r["test_change"] == "0")
sample = [(s, "positive") for s in rng.sample(pos, 50)] + [(s, "negative_test_change") for s in rng.sample(neg_t, 40)] + \
         [(s, "negative_no_test_change") for s in rng.sample(neg_n, 10)]
O = ROOT / "validation/human_r4"; O.mkdir(exist_ok=True)
with open(O / "set3_sample.csv", "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["sha", "repo", "stratum", "stratum_size"])
    size = {"positive": len(pos), "negative_test_change": len(neg_t), "negative_no_test_change": len(neg_n)}
    for s, st in sample:
        w.writerow([s, commits[s]["repo"], st, size[st]])
with open(O / "set3_items.jsonl", "w") as fh:
    for s, _ in sample:
        dt = details[s]
        tl = [{"file": t["file"], "added": t["added"][:60]} for t in dt["test_added"]]
        fh.write(json.dumps({"sha": s, "repo": commits[s]["repo"], "message": dt["message"][:4000], "files": dt["files"][:80],
                             "tests": tl, "patch": "\n".join(dt["patch"].split("\n")[:160])}, ensure_ascii=False) + "\n")
print(json.dumps({"lineages": len(rows), "locale_test_line": k, "share": round(k / len(rows), 4),
                  "strata": {"positive": len(pos), "negative_test_change": len(neg_t), "negative_no_test_change": len(neg_n)},
                  "sample": len(sample)}, indent=1))
