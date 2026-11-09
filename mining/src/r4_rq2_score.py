"""Round-4 RQ2 real-code evaluation, step 3 (exploratory; protocol/DEVIATIONS.md, 2026-11-09).

Usage: python3 src/r4_rq2_score.py <tool_out_dir>
Inputs: data/processed/realcode_files.csv, data/processed/repair_edits.csv, the files in data/raw/r4/realcode/, the
tool outputs of scripts/r4_rq2_run_tools.sh in <tool_out_dir>, and the model labels of the coded samples.

Each matched edit is located in the parent file (its removed line) and in the repair file (its added line), by
whitespace-stripped equality. A finding flags an edit side when it starts on such a line and its rule is
locale-relevant: every prototype rule; the PMD rule UseLocaleWithCaseConversions; a Semgrep registry rule whose id
contains locale, culture, collat, tolower, toupper, lowercase, uppercase or case-conv (fixed before parsing).
A lineage side is flagged when any of its located edits is flagged on that side.

Categories (model labels; round-4 rules of src/r4_rq1_analyses.py): pinning of machine text (role-consistent),
pinning of linguistic text (misfit), locale-aware change on linguistic text (role-consistent), locale-aware change
on machine text (misfit, role-neutral and engine-dependent cases split out). A role-aware rule would flag the
version that misfits: the parent for role-consistent changes, the repair for misfits.
Writes results/r4_rq2_realcode.json.
"""
import csv, json, pathlib, re, sys, collections

ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOLS = pathlib.Path(sys.argv[1])
RAW = ROOT / "data/raw/r4/realcode"
sys.path.insert(0, str(ROOT / "src"))

REG_RELEVANT = re.compile(r"locale|culture|collat|tolower|toupper|lowercase|uppercase|case-conv", re.I)

# ---------- findings: (sha, side, path) -> {line: set(rules)} ----------
find = {t: collections.defaultdict(lambda: collections.defaultdict(set)) for t in ("prototype", "registry", "pmd")}


def key_of(path):
    p = pathlib.PurePosixPath(path).parts
    i = p.index("src") if "src" in p and p[0] in ("/", "src") else -1
    rel = p[i + 1:] if i >= 0 else p
    return rel[0], rel[1], "/".join(rel[2:])


for tool, fname in (("prototype", "semgrep_prototype.json"), ("registry", "semgrep_registry.json")):
    d = json.load(open(TOOLS / fname))
    for r in d.get("results", []):
        rule = r["check_id"].split(".")[-1]
        if tool == "registry" and not REG_RELEVANT.search(r["check_id"]):
            continue
        sha, side, path = key_of(r["path"])
        find[tool][(sha, side, path)][r["start"]["line"]].add(rule)
pmd = json.load(open(TOOLS / "pmd.json"))
for f in pmd.get("files", []):
    sha, side, path = key_of(f["filename"])
    for v in f.get("violations", []):
        if v["rule"] == "UseLocaleWithCaseConversions":
            find["pmd"][(sha, side, path)][v["beginline"]].add(v["rule"])

# ---------- locate edits ----------
files = {(r["sha"], r["file"]): r for r in csv.DictReader(open(ROOT / "data/processed/realcode_files.csv"))}
edits = collections.defaultdict(list)
for e in csv.DictReader(open(ROOT / "data/processed/repair_edits.csv")):
    if (e["sha"], e["file"]) in files:
        edits[e["sha"]].append(e)


def lines_of(sha, side, path):
    p = RAW / sha / side / path
    return p.read_text(errors="replace").splitlines() if p.exists() else None


located = collections.Counter()
lineage = collections.defaultdict(lambda: {t: {"pre": False, "post": False} for t in find})
lineage_loc = collections.defaultdict(lambda: {"pre": False, "post": False})
for sha, es in edits.items():
    for e in es:
        fr = files[(sha, e["file"])]
        for side, text, path in (("pre", e["removed"], fr["pre_path"]), ("post", e["added"], e["file"])):
            L = lines_of(sha, side, path)
            if L is None:
                located[side + "_file_missing"] += 1; continue
            want = text.strip()
            nums = [i + 1 for i, l in enumerate(L) if l.strip() == want]
            if not nums:
                located[side + "_line_not_found"] += 1; continue
            located[side + "_located"] += 1; lineage_loc[sha][side] = True
            for t in find:
                hits = find[t].get((sha, side, path), {})
                if any(n in hits for n in nums):
                    lineage[sha][t][side] = True

# ---------- categories from the model labels ----------
import contextlib, io  # noqa: E402
with contextlib.redirect_stdout(io.StringIO()):
    import r4_rq1_analyses as R  # recomputes the round-4 labels (deterministic; rewrites results/r4_rq1.json identically)
cat = {}
for i in R.g:
    sha = R.key[i]["sha"]; ds = R.dirs(sha); role = R.adj[i]["role"]
    if ds == ["MACHINE_PINNING"]:
        cat[sha] = {"MACHINE": "pin_machine", "LINGUISTIC": "pin_linguistic_misfit"}.get(role)
    elif ds == ["LINGUISTIC_REPAIR"]:
        cat[sha] = {"LINGUISTIC": "aware_linguistic", "MACHINE": "aware_machine_misfit"}.get(role)
lkey = {r["item_id"]: r["sha"] for r in csv.DictReader(open(ROOT / "validation/ling/key.csv"))}
for i in R.aware:
    sha = lkey[i]
    if R.fin[i]["role"] == "LINGUISTIC":
        cat.setdefault(sha, "aware_linguistic")
    elif R.fin[i]["role"] == "MACHINE":
        c = "aware_machine_role_neutral" if i in R.neutral_new else "aware_machine_engine_dependent" if i in R.engine else "aware_machine_misfit"
        cat[sha] = c
ideal = {"pin_machine": "pre", "pin_linguistic_misfit": "post", "aware_linguistic": "pre", "aware_machine_misfit": "post",
         "aware_machine_engine_dependent": "post", "aware_machine_role_neutral": None}

summary = {}
for c in ideal:
    shas = [s for s in lineage_loc if cat.get(s) == c and lineage_loc[s]["pre"] and lineage_loc[s]["post"]]
    row = {"lineages_located_both_sides": len(shas), "ideal_flag_side": ideal[c]}
    for t in find:
        row[t] = {"flag_pre": sum(lineage[s][t]["pre"] for s in shas), "flag_post": sum(lineage[s][t]["post"] for s in shas),
                  "flag_only_ideal_side": sum(1 for s in shas if ideal[c] and lineage[s][t][ideal[c]] and not lineage[s][t]["post" if ideal[c] == "pre" else "pre"])}
    summary[c] = row
out = {"edit_sides": dict(located), "lineages_with_files": len(lineage_loc), "categories": summary,
       "findings_files": {t: len(find[t]) for t in find},
       "semgrep_version": (TOOLS / "semgrep_version.txt").read_text().strip() if (TOOLS / "semgrep_version.txt").exists() else None}
json.dump(out, open(ROOT / "results/r4_rq2_realcode.json", "w"), indent=1)
print(json.dumps(out, indent=1))
