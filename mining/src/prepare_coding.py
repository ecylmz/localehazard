"""Draw the RQ3 validation sample (seeded) and write blinded coder packages."""
import csv, gzip, json, pathlib, random, re

ROOT = pathlib.Path(__file__).resolve().parents[1]
P = ROOT / "data/processed"; C = ROOT / "data/raw/commits"
OUT = ROOT / "validation"; OUT.mkdir(exist_ok=True)
SEED, N_INC, N_NEG = 20261004, 150, 60
TURKIC_Q = {"T1", "T2", "T3", "T4", "T5"}


def excerpt(commit, wanted_removed):
    lines = []
    for f in commit.get("files", []):
        patch = f.get("patch") or ""
        if not patch:
            continue
        hunks = re.split(r"(?m)^(?=@@)", patch)
        keep = [h for h in hunks if any(w and w in re.sub(r"\s+", " ", h) for w in wanted_removed)] if wanted_removed else hunks[:2]
        for h in keep[:3]:
            lines.append(f"--- {f['filename']}")
            lines.extend(h.splitlines()[:30])
        if len(lines) > 80:
            break
    return "\n".join(lines[:80])


def main():
    lin = list(csv.DictReader(open(P / "commits_lineages.csv")))
    reps = sorted(r["sha"] for r in lin if r["lineage_representative"] == "1")
    commits = {r["sha"]: r for r in csv.DictReader(open(P / "commits_classified.csv"))}
    edits = {}
    for e in csv.DictReader(open(P / "repair_edits.csv")):
        edits.setdefault(e["sha"], []).append(e)
    rng = random.Random(SEED)
    inc = rng.sample(reps, N_INC)
    included_shas = {r["sha"] for r in lin}
    neg_pool = sorted(s for s, c in commits.items() if c["fetch_status"] == "200" and s not in included_shas
                      and c.get("format_only") == "0" and set(c["queries"].split(";")) & TURKIC_Q)
    neg = rng.sample(neg_pool, min(N_NEG, len(neg_pool)))
    items, key = [], []
    for kind, shas in (("included", inc), ("excluded", neg)):
        for s in shas:
            c = json.load(gzip.open(C / f"{s}.json.gz", "rt"))
            ed = edits.get(s, []) if kind == "included" else []
            items.append({"sha": s, "repo": c["repo"], "message": c["message"][:1500],
                          "matched_edits": [{"file": e["file"], "removed": e["removed"], "added": e["added"]} for e in ed[:10]],
                          "patch_excerpt": excerpt(c, [e["removed"][:60] for e in ed[:10]])})
            key.append({"sha": s, "sample": kind})
    rng.shuffle(items)
    for i, it in enumerate(items):
        it["item_id"] = f"I{i + 1:03d}"
    batch = 53
    for b in range(0, len(items), batch):
        with open(OUT / f"coding_batch_{b // batch + 1:02d}.jsonl", "w") as fh:
            for it in items[b:b + batch]:
                fh.write(json.dumps({k: it[k] for k in ("item_id", "repo", "message", "matched_edits", "patch_excerpt")}, ensure_ascii=False) + "\n")
    idmap = {it["sha"]: it["item_id"] for it in items}
    with open(OUT / "sample_key.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["item_id", "sha", "sample"]); w.writeheader()
        for k in key: w.writerow({"item_id": idmap[k["sha"]], **k})
    print("items", len(items), "batches", (len(items) + batch - 1) // batch, "neg_pool", len(neg_pool))


if __name__ == "__main__":
    main()
