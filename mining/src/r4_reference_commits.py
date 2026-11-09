"""Round-4 reference rate (protocol/DEVIATIONS.md, 2026-11-09): how often do other commits of the same repositories
touch a test file or add a locale-test line?

For each repository that holds a lineage representative, the calendar year of its earliest representative repair is
taken. Two non-merge commits of that year that are not in any included lineage are drawn at random (seed 20261109):
the commit list of the year is read from a random page of the GitHub commits API (100 per page), and two commits
are drawn from that page. Each drawn commit is fetched with its files. The same TEST_PATH rule and the same LOCTEST
expression as for the lineages decide test_change and locale_test_line.

Usage: python3 src/r4_reference_commits.py [--limit N] [--out-raw DIR]
The GitHub token is read from the environment (GH_TOKEN) or from `gh auth token` at run time; it is never written.
Raw responses: data/raw/r4/reference/<owner>__<repo>.json.gz (not redistributed). Per-commit table:
data/processed/reference_commits.csv. Failures (repository gone, empty year, API error) are recorded, not imputed.
"""
import argparse, csv, gzip, json, os, pathlib, random, re, subprocess, sys, time, urllib.error, urllib.parse, urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from classify_diffs import TEST_PATH
from r4_loctest_indicators_rules import LOCTEST

ap = argparse.ArgumentParser()
ap.add_argument("--limit", type=int, default=0)
ap.add_argument("--out-raw", default=str(ROOT / "data/raw/r4/reference"))
ap.add_argument("--out-csv", default=str(ROOT / "data/processed/reference_commits.csv"))
args = ap.parse_args()
RAW = pathlib.Path(args.out_raw); RAW.mkdir(parents=True, exist_ok=True)
TOKEN = os.environ.get("GH_TOKEN") or subprocess.run(["gh", "auth", "token"], capture_output=True, text=True).stdout.strip()
HDR = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json", "User-Agent": "localehazard-study",
       "X-GitHub-Api-Version": "2022-11-28"}


def api(url):
    for attempt in range(6):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=HDR), timeout=60) as r:
                rem, reset = int(r.headers.get("X-RateLimit-Remaining", "1")), int(r.headers.get("X-RateLimit-Reset", "0"))
                body = json.loads(r.read().decode()); link = r.headers.get("Link", "")
                if rem < 20:
                    time.sleep(max(0, reset - time.time()) + 5)
                return 200, body, link
        except urllib.error.HTTPError as e:
            if e.code in (403, 429):
                reset = int(e.headers.get("X-RateLimit-Reset", "0") or 0)
                time.sleep(max(30, reset - time.time() + 5) if reset else 60 * (attempt + 1)); continue
            if e.code in (404, 409, 410, 451):
                return e.code, None, ""
            time.sleep(10 * (attempt + 1))
        except Exception:
            time.sleep(10 * (attempt + 1))
    return -1, None, ""


P = ROOT / "data/processed"
commits = {r["sha"]: r for r in csv.DictReader(open(P / "commits_classified.csv"))}
lin = list(csv.DictReader(open(P / "commits_lineages.csv")))
included = {r["sha"] for r in lin}
first = {}
for r in lin:
    if r["lineage_representative"] != "1":
        continue
    c = commits[r["sha"]]; d = c["committer_date"] or ""
    if d and (c["repo"].lower() not in first or d < first[c["repo"].lower()][1]):
        first[c["repo"].lower()] = (c["repo"], d)
repos = sorted(first.values())
rng = random.Random(20261109)
plan = [(repo, d[:4], rng.random()) for repo, d in repos]  # one random draw per repo, fixed before any request
if args.limit:
    plan = plan[:args.limit]

rows = []
for n, (repo, year, u) in enumerate(plan, 1):
    f = RAW / (repo.replace("/", "__") + ".json.gz")
    if f.exists():
        rec = json.load(gzip.open(f, "rt"))
    else:
        q = urllib.parse.urlencode({"since": f"{year}-01-01T00:00:00Z", "until": f"{year}-12-31T23:59:59Z", "per_page": 100})
        base = f"https://api.github.com/repos/{repo}/commits?{q}"
        st, body, link = api(base + "&page=1")
        rec = {"repo": repo, "year": year, "status": st, "page": 1, "commits": []}
        if st == 200 and body:
            m = re.search(r'[?&]page=(\d+)>; rel="last"', link)
            last = int(m.group(1)) if m else 1
            page = 1 + int(u * last) if last > 1 else 1
            if page != 1:
                st, body, _ = api(base + f"&page={page}"); rec["page"] = page; rec["status"] = st
            cand = [c["sha"] for c in (body or []) if len(c.get("parents", [])) == 1 and c["sha"] not in included]
            rr = random.Random(f"{repo}:{year}:20261109")
            for sha in rr.sample(cand, min(2, len(cand))):
                st2, cb, _ = api(f"https://api.github.com/repos/{repo}/commits/{sha}")
                if st2 == 200 and cb:
                    rec["commits"].append({"sha": sha, "files": [{"filename": x["filename"], "patch": x.get("patch")} for x in cb.get("files", [])]})
                else:
                    rec["commits"].append({"sha": sha, "status": st2})
            rec["candidates"] = len(cand); rec["last_page"] = last
        json.dump(rec, gzip.open(f, "wt"))
    for c in rec.get("commits", []):
        if "files" not in c:
            rows.append({"repo": repo, "year": year, "sha": c["sha"], "status": c.get("status"), "test_change": "", "locale_test_line": "", "n_files": ""})
            continue
        tf = [x for x in c["files"] if TEST_PATH.search(x["filename"])]
        loc = any(LOCTEST.search(l) for x in tf for l in (x.get("patch") or "").split("\n") if l.startswith("+") and not l.startswith("+++"))
        rows.append({"repo": repo, "year": year, "sha": c["sha"], "status": 200, "test_change": int(bool(tf)),
                     "locale_test_line": int(loc), "n_files": len(c["files"])})
    if not rec.get("commits"):  # repository gone, empty year, or no eligible commit on the drawn page
        st = rec.get("status")
        rows.append({"repo": repo, "year": year, "sha": "", "status": "no_candidates" if st == 200 else st, "test_change": "", "locale_test_line": "", "n_files": ""})
    if n % 50 == 0:
        print(f"{n}/{len(plan)} repositories", flush=True)

with open(args.out_csv, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
ok = [r for r in rows if r["status"] == 200]
print(json.dumps({"repositories": len(plan), "commits": len(ok), "failures": len(rows) - len(ok),
                  "test_change": sum(r["test_change"] for r in ok), "locale_test_line": sum(r["locale_test_line"] for r in ok)}))
