"""PLANNED (protocol A2, set before RQ3 outcomes were inspected): residual locale-sensitive call sites.

For a seeded random sample of included JVM and .NET repair commits, fetch each file the classifier
repaired at the post-commit revision and count remaining no-argument default-locale case-mapping calls:
JVM `.toLowerCase()` / `.toUpperCase()` (excluding Kotlin `lowercase()`), .NET `.ToLower()` / `.ToUpper()`.
A residual call is not necessarily a defect (its text may be linguistic); the measure bounds how far a
repair commit generalized within the files it touched.
"""
import csv, json, pathlib, random, re, subprocess, time, urllib.request, urllib.error, urllib.parse
from concurrent.futures import ThreadPoolExecutor

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "data/raw/residual"; OUT.mkdir(parents=True, exist_ok=True)
TOKEN = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True).stdout.strip()
SEED, N = 20261002, 400
PAT = {"jvm": re.compile(r"\.to(Lower|Upper)Case\(\s*\)"), "dotnet": re.compile(r"\.To(Lower|Upper)\(\s*\)")}
COMMENT = re.compile(r"^\s*(//|\*|/\*)")


def fetch(repo, sha, path):
    url = f"https://raw.githubusercontent.com/{repo}/{sha}/{urllib.parse.quote(path)}"
    for a in range(4):
        try:
            req = urllib.request.Request(url, headers={"Authorization": f"token {TOKEN}", "User-Agent": "cdm-study"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(5 * (a + 1))
        except Exception:
            time.sleep(5 * (a + 1))
    return None


def main():
    commits = {r["sha"]: r for r in csv.DictReader(open(ROOT / "data/processed/commits_lineages.csv")) if r["lineage_representative"] == "1"}
    edits = [e for e in csv.DictReader(open(ROOT / "data/processed/repair_edits.csv"))
             if e["sha"] in commits and e["ecosystem"] in PAT and e["op"] == "CASE" and e["direction"] == "MACHINE_PINNING"]
    shas = sorted({e["sha"] for e in edits})
    random.Random(SEED).shuffle(shas)
    sample = shas[:N]
    files = sorted({(e["sha"], e["repo"], e["file"], e["ecosystem"]) for e in edits if e["sha"] in set(sample)})

    def one(t):
        sha, repo, path, eco = t
        txt = fetch(repo, sha, path)
        if txt is None:
            return {"sha": sha, "repo": repo, "file": path, "ecosystem": eco, "fetched": 0, "residual_calls": ""}
        n = sum(len(PAT[eco].findall(l)) for l in txt.splitlines() if not COMMENT.match(l))
        return {"sha": sha, "repo": repo, "file": path, "ecosystem": eco, "fetched": 1, "residual_calls": n}

    with ThreadPoolExecutor(8) as ex:
        rows = list(ex.map(one, files))
    with open(ROOT / "data/processed/residual_sites.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    print("sampled commits", len(sample), "files", len(rows), "fetched", sum(r["fetched"] for r in rows))


if __name__ == "__main__":
    main()
