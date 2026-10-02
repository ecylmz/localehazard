"""Fetch commit patches (and repository metadata) for the deduplicated RQ3 search hits.

Deduplication before fetching: one record per SHA; a non-fork copy is preferred; merge commits are skipped.
Rate-limit aware; resumable (one gzip JSON per commit under data/raw/commits/).
"""
import gzip, json, os, pathlib, subprocess, sys, threading, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor

ROOT = pathlib.Path(__file__).resolve().parents[1]
SEARCH = ROOT / "data/raw/search"
CDIR = ROOT / "data/raw/commits"; CDIR.mkdir(parents=True, exist_ok=True)
RDIR = ROOT / "data/raw/repos"; RDIR.mkdir(parents=True, exist_ok=True)
def _token():
    try:
        return subprocess.run(["gh", "auth", "token"], capture_output=True, text=True).stdout.strip()
    except FileNotFoundError:
        import os as _os
        return _os.environ.get("GITHUB_TOKEN", "")


TOKEN = _token()
HITS = ROOT / "data/raw/search_hits.csv.gz"  # compact export of data/raw/search/*.jsonl
(ROOT / "logs").mkdir(exist_ok=True)
LOG = open(ROOT / "logs/fetch_details.log", "a")
lock = threading.RLock()
import re
# Malformed queries whose reported totals show that GitHub tokenized the identifier (see protocol/DEVIATIONS.md):
LITERAL_FILTER = {"A5": re.compile(r"DM_CONVERT_CASE"), "C1": re.compile(r"g_ascii_strcasecmp"), "C2": re.compile(r"ascii_tolower"), "S2": re.compile(r"to_ascii_lowercase")}
state = {"remaining": 5000, "reset": 0}


def log(*a):
    s = " ".join(map(str, a))
    with lock:
        LOG.write(s + "\n"); LOG.flush()


def get(url):
    for attempt in range(8):
        with lock:
            if state["remaining"] < 50:
                wait = max(5, state["reset"] - time.time() + 5)
                log("RATE_WAIT", int(wait)); time.sleep(wait); state["remaining"] = 5000
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json",
                                                   "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "cdm-study"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                with lock:
                    state["remaining"] = int(r.headers.get("X-RateLimit-Remaining", 5000))
                    state["reset"] = int(r.headers.get("X-RateLimit-Reset", 0))
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code in (404, 409, 410, 422, 451):
                return e.code, None
            if e.code in (403, 429):
                ra = e.headers.get("Retry-After"); reset = e.headers.get("X-RateLimit-Reset")
                wait = int(ra) if ra else (max(5, int(reset) - time.time() + 5) if reset else 60 * (attempt + 1))
                log("HTTP", e.code, "wait", int(wait), url); time.sleep(min(wait, 3700)); continue
            log("HTTP", e.code, url); time.sleep(10 * (attempt + 1))
        except Exception as e:  # network
            log("NET", repr(e)[:120], url); time.sleep(10 * (attempt + 1))
    return -1, None


def iter_search_rows():
    """Yield retrieved search hits from the raw JSONL responses, or from the compact CSV export."""
    files = sorted(SEARCH.glob("*.jsonl"))
    if files:
        for f in files:
            for line in open(f):
                r = json.loads(line)
                if r["query"] in LITERAL_FILTER:
                    r["literal_match"] = int(bool(LITERAL_FILTER[r["query"]].search(r["message"])))
                yield r
        return
    import csv as _csv
    with gzip.open(HITS, "rt", newline="") as fh:
        for r in _csv.DictReader(fh):
            r["parents"] = int(r["parents"]); r["fork"] = r["fork"] == "True"
            r["literal_match"] = int(r["literal_match"]) if r["literal_match"] != "" else None
            r["message"] = r.pop("subject"); r["author_date"] = None
            yield r


def candidates():
    by_sha = {}
    for r in iter_search_rows():
            if r["parents"] != 1:
                continue
            if r["query"] in LITERAL_FILTER and not r["literal_match"]:
                continue
            cur = by_sha.get(r["sha"])
            if cur is None:
                r["queries"] = {r["query"]}; by_sha[r["sha"]] = r
            else:
                cur["queries"].add(r["query"])
                if cur["fork"] and not r["fork"]:
                    r["queries"] = cur["queries"]; by_sha[r["sha"]] = r
    return by_sha


def fetch_commit(r):
    out = CDIR / f"{r['sha']}.json.gz"
    if out.exists():
        return
    st, d = get(f"https://api.github.com/repos/{r['repo']}/commits/{r['sha']}")
    rec = {"sha": r["sha"], "repo": r["repo"], "status": st, "queries": sorted(r["queries"]), "fork": r["fork"],
           "message": r["message"], "committer_date": r["committer_date"], "author_date": r["author_date"]}
    if d:
        rec["stats"] = d.get("stats")
        rec["files"] = [{"filename": f["filename"], "status": f.get("status"), "additions": f.get("additions"),
                         "deletions": f.get("deletions"), "patch": (f.get("patch") or "")[:400_000]} for f in d.get("files", [])]
        rec["n_files_api"] = len(d.get("files", []))
    with gzip.open(out, "wt") as fh:
        json.dump(rec, fh)


def fetch_repo(name):
    out = RDIR / (name.replace("/", "__") + ".json")
    if out.exists():
        return
    st, d = get(f"https://api.github.com/repos/{name}")
    keep = {"status": st}
    if d:
        keep.update({k: d.get(k) for k in ("full_name", "fork", "stargazers_count", "forks_count", "language", "created_at",
                                             "pushed_at", "archived", "size")})
        keep["parent"] = (d.get("parent") or {}).get("full_name")
    out.write_text(json.dumps(keep))


def main():
    loop = "--loop" in sys.argv
    while True:
        c = candidates()
        todo = [r for r in c.values() if not (CDIR / f"{r['sha']}.json.gz").exists()]
        log("ROUND candidates", len(c), "todo", len(todo))
        with ThreadPoolExecutor(8) as ex:
            list(ex.map(fetch_commit, todo))
        repos = sorted({r["repo"] for r in c.values()}) if os.environ.get("FETCH_REPOS") == "all" else []
        if os.environ.get("FETCH_REPOS") == "included":
            import csv as _csv
            repos = sorted({r["repo"] for r in _csv.DictReader(open(ROOT / "data/processed/commits_classified.csv")) if r.get("included") == "1"})
        with ThreadPoolExecutor(8) as ex:
            list(ex.map(fetch_repo, repos))
        done = (ROOT / "logs/retrieve_commits.log").read_text().strip().endswith("ALLDONE")
        if not loop or (done and not todo):
            break
        if not todo:
            time.sleep(120)
    log("FETCH_DONE")


if __name__ == "__main__":
    main()
