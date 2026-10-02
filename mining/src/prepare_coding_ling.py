"""POST_HOC: package every linguistic-direction repair lineage for role-only coding by two coders."""
import csv, gzip, json, pathlib, random, sys
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from prepare_coding import excerpt
lin = {r["sha"] for r in csv.DictReader(open(ROOT / "data/processed/commits_lineages.csv")) if r["lineage_representative"] == "1"}
ed = {}
for e in csv.DictReader(open(ROOT / "data/processed/repair_edits.csv")):
    if e["sha"] in lin and e["direction"] == "LINGUISTIC_REPAIR":
        ed.setdefault(e["sha"], []).append(e)
shas = sorted(ed); random.Random(20261005).shuffle(shas)
out = ROOT / "validation/ling"; out.mkdir(parents=True, exist_ok=True)
with open(out / "items.jsonl", "w") as fh, open(out / "key.csv", "w", newline="") as kf:
    w = csv.writer(kf); w.writerow(["item_id", "sha"])
    for i, s in enumerate(shas):
        c = json.load(gzip.open(ROOT / f"data/raw/commits/{s}.json.gz", "rt"))
        it = {"item_id": f"L{i + 1:03d}", "repo": c["repo"], "message": c["message"][:800],
              "changed_lines": [{"file": e["file"], "removed": e["removed"], "added": e["added"]} for e in ed[s][:6]],
              "patch_excerpt": excerpt(c, [e["removed"][:60] for e in ed[s][:6]])[:2500]}
        fh.write(json.dumps(it, ensure_ascii=False) + "\n"); w.writerow([it["item_id"], s])
print(len(shas))
