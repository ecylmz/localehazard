"""Round-4 RQ2 real-code evaluation, step 1 (exploratory; protocol/DEVIATIONS.md, 2026-11-09).

For every coded RQ1 lineage (the 133 genuine validation-sample changes and the 181 opposite-direction lineages),
fetch each Java, Kotlin, C#, JavaScript and TypeScript file that holds a matched edit, at the repair commit (post)
and at its first parent (pre). Files go to data/raw/r4/realcode/<sha>/{pre,post}/<path> (not redistributed); the
manifest data/processed/realcode_files.csv records every file and every failure. Needs the raw commit JSON in
data/raw/commits/ for the parent SHA and renames. Token from GH_TOKEN or `gh auth token`; never written.
"""
import csv, gzip, json, os, pathlib, subprocess, time, urllib.error, urllib.parse, urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "data/raw/r4/realcode"
TOKEN = os.environ.get("GH_TOKEN") or subprocess.run(["gh", "auth", "token"], capture_output=True, text=True).stdout.strip()
EXT = {"java", "kt", "cs", "js", "jsx", "ts", "tsx", "mjs"}

key = {r["item_id"]: r for r in csv.DictReader(open(ROOT / "validation/sample_key.csv"))}
adj = {r["item_id"]: r for r in csv.DictReader(open(ROOT / "validation/adjudicated.csv"))}
inc = {r["sha"] for r in csv.DictReader(open(ROOT / "data/processed/commits_lineages.csv"))}
coded = {key[i]["sha"] for i in key if key[i]["sample"] == "included" and key[i]["sha"] in inc and adj[i]["genuine"] == "YES"}
coded |= {r["sha"] for r in csv.DictReader(open(ROOT / "validation/ling/key.csv"))}
edits = [e for e in csv.DictReader(open(ROOT / "data/processed/repair_edits.csv"))
         if e["sha"] in coded and e["file"].rsplit(".", 1)[-1].lower() in EXT]
files = sorted({(e["sha"], e["repo"], e["file"]) for e in edits})


def fetch(repo, ref, path):
    url = f"https://raw.githubusercontent.com/{repo}/{ref}/{urllib.parse.quote(path)}"
    for a in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"Authorization": f"token {TOKEN}", "User-Agent": "localehazard-study"}), timeout=60) as r:
                return 200, r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return 404, None
            time.sleep(5 * (a + 1))
        except Exception:
            time.sleep(5 * (a + 1))
    return -1, None


# The raw commit JSON of the mining step holds no parent SHA; read it once per commit from the GitHub API (cached).
PCACHE = OUT / "_parents.json"
parents = json.loads(PCACHE.read_text()) if PCACHE.exists() else {}


def parent_of(repo, sha):
    if sha not in parents:
        url = f"https://api.github.com/repos/{repo}/commits/{sha}"
        for a in range(4):
            try:
                req = urllib.request.Request(url, headers={"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json", "User-Agent": "localehazard-study"})
                with urllib.request.urlopen(req, timeout=60) as r:
                    parents[sha] = (json.loads(r.read().decode()).get("parents") or [{}])[0].get("sha", ""); break
            except urllib.error.HTTPError as e:
                if e.code in (404, 409, 422):
                    parents[sha] = ""; break
                time.sleep(10 * (a + 1))
            except Exception:
                time.sleep(10 * (a + 1))
        OUT.mkdir(parents=True, exist_ok=True); PCACHE.write_text(json.dumps(parents))
    return parents.get(sha, "")


rows = []
for n, (sha, repo, path) in enumerate(files, 1):
    c = json.load(gzip.open(ROOT / f"data/raw/commits/{sha}.json.gz", "rt"))
    parent = parent_of(repo, sha)
    prev = next((f.get("previous_filename") or path for f in c.get("files", []) if f["filename"] == path), path)
    row = {"sha": sha, "repo": repo, "file": path, "parent": parent, "pre_path": prev}
    for side, ref, p in (("post", sha, path), ("pre", parent, prev)):
        dst = OUT / sha / side / path
        if dst.exists():
            row[side] = 200; continue
        st, body = fetch(repo, ref, p) if ref else (-2, None)
        row[side] = st
        if st == 200:
            dst.parent.mkdir(parents=True, exist_ok=True); dst.write_bytes(body)
    rows.append(row)
    if n % 100 == 0:
        print(f"{n}/{len(files)} files", flush=True)
with open(ROOT / "data/processed/realcode_files.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
print(json.dumps({"lineages": len({r['sha'] for r in rows}), "files": len(rows),
                  "post_ok": sum(r["post"] == 200 for r in rows), "pre_ok": sum(r["pre"] == 200 for r in rows)}))
