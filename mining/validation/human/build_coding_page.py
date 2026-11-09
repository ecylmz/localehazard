"""Build the blinded human-coding page (validation/human/human_coding.html).

Set 1: all 210 items of the RQ1 validation sample (150 included + 60 excluded), shown with message and
patch excerpt only (no classifier matches, which would reveal excluded items), under new IDs in a seeded order.
Set 2: all 181 opposite-direction lineages, with their matched edit lines, under new IDs in a seeded order.
No model label, note, or aggregate is embedded. The ID key is written to key.csv (keep it away from coders).
"""
import csv, json, pathlib, random

ROOT = pathlib.Path(__file__).resolve().parents[2]
V = ROOT / "validation"
OUT = pathlib.Path(__file__).resolve().parent
rng = random.Random(20261030)

sha1 = {r["item_id"]: r["sha"] for r in csv.DictReader(open(V / "sample_key.csv"))}
s1 = [json.loads(l) for k in range(1, 5) for l in open(V / f"coding_batch_0{k}.jsonl")]
rng.shuffle(s1)
sha2 = {r["item_id"]: r["sha"] for r in csv.DictReader(open(V / "ling/key.csv"))}
s2 = [json.loads(l) for l in open(V / "ling/items.jsonl")]
rng.shuffle(s2)

items, key = [], []
for n, it in enumerate(s1, 1):
    hid = f"A{n:03d}"
    key.append({"human_id": hid, "set": "1", "orig_id": it["item_id"], "sha": sha1[it["item_id"]]})
    items.append({"id": hid, "set": 1, "repo": it["repo"], "sha": sha1[it["item_id"]], "message": it["message"],
                  "patch": it["patch_excerpt"]})
for n, it in enumerate(s2, 1):
    hid = f"B{n:03d}"
    cl = it["changed_lines"] if isinstance(it["changed_lines"], list) else []
    key.append({"human_id": hid, "set": "2", "orig_id": it["item_id"], "sha": sha2[it["item_id"]]})
    items.append({"id": hid, "set": 2, "repo": it["repo"], "sha": sha2[it["item_id"]], "message": it["message"],
                  "edits": [{"file": c.get("file", ""), "removed": c.get("removed", ""), "added": c.get("added", "")} for c in cl],
                  "patch": it["patch_excerpt"]})

with open(OUT / "key.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(key[0])); w.writeheader(); w.writerows(key)
data = json.dumps(items, ensure_ascii=False).replace("</", "<\\/")
html = (OUT / "template.html").read_text().replace("__DATA__", data)
(OUT / "human_coding.html").write_text(html.replace("__CODER__", ""))
# one copy per coder with the coder name fixed, so answers and exports cannot be mixed up
(OUT / "for_coders").mkdir(exist_ok=True)
for n, coder in ((1, "D1"), (2, "D2")):
    (OUT / "for_coders" / f"degerlendirici_{n}.html").write_text(html.replace("__CODER__", coder))
print(len(items), "items;", sum(1 for i in items if i["set"] == 1), "in set 1;", sum(1 for i in items if i["set"] == 2), "in set 2")
