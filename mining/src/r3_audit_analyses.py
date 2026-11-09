"""Round-3 audit analyses (post hoc, after the abstract/content audit in review/report_R3_*.md).

All inputs are existing result files; no new data were collected.
(a) lineage sensitivity: grouping by identical edits within a repository instead of globally;
(b) role fit in the coded sample with role-neutral changes (case folding, fixed English locale) separated;
(c) context-bearing probes with X3 (sort/search comparator agreement) reported as a control;
(d) majority-class baseline for the lexical role cues;
(e) unit and breakdown checks used in the text.
"""
import csv, json, pathlib, re, collections, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from analyze_mining import boot_share, VENDORED
from analyze_validation import wilson

P = ROOT / "data/processed"
commits = {r["sha"]: r for r in csv.DictReader(open(P / "commits_classified.csv"))}
lin = list(csv.DictReader(open(P / "commits_lineages.csv")))
included = {r["sha"] for r in lin}
reps = [commits[r["sha"]] for r in lin if r["lineage_representative"] == "1"]
edits = collections.defaultdict(list)
for e in csv.DictReader(open(P / "repair_edits.csv")):
    if not VENDORED.search(e["file"]):
        edits[e["sha"]].append(e)
repo = lambda c: c["repo"].lower()
dirs = lambda c: sorted({e["direction"] for e in edits[c["sha"]]})
out = {}

# (a) within-repository grouping
groups = collections.defaultdict(list)
for s in sorted(included):  # sorted: set order depends on PYTHONHASHSEED (round 4)
    c = commits[s]
    groups[(repo(c), tuple(sorted(e["removed"] + "→" + e["added"] for e in edits[s])))].append(c)
wr = [sorted(g, key=lambda c: (c["committer_date"] or "", c["sha"]))[0] for g in groups.values()]
out["within_repo"] = {"groups": len(wr), "repositories": len({repo(c) for c in wr}),
                      "pinning_only": boot_share(wr, lambda c: dirs(c) == ["MACHINE_PINNING"], repo),
                      "test_change": boot_share(wr, lambda c: c["test_change"] == "1", repo)}
out["global"] = {"pinning_only": boot_share(reps, lambda c: dirs(c) == ["MACHINE_PINNING"], repo),
                 "test_change": boot_share(reps, lambda c: c["test_change"] == "1", repo),
                 "repositories_with_included_commits": len({repo(commits[s]) for s in included})}
sites = [len(edits[c["sha"]]) for c in reps]
out["edited_line_pairs"] = {"le2_share": round(sum(1 for x in sites if x <= 2) / len(sites), 4), "one_share": round(sum(1 for x in sites if x == 1) / len(sites), 4)}

# (b) role fit with role-neutral changes separated
key = {r["item_id"]: r for r in csv.DictReader(open(ROOT / "validation/sample_key.csv"))}
adj = {r["item_id"]: r for r in csv.DictReader(open(ROOT / "validation/adjudicated.csv"))}
g = [i for i in key if key[i]["sample"] == "included" and key[i]["sha"] in included and adj[i]["genuine"] == "YES"]
FOLD = re.compile(r"\.casefold\(|ToLowerInvariant|fold", re.I)
ENGLISH = re.compile(r"toLocale(Lower|Upper)Case\(\s*\[?\s*['\"]en|Locale\.(ENGLISH|US|UK)\b|CultureInfo\(\s*\"en", re.I)
def neutral(sha):
    """An opposite-direction change whose new semantics equal locale-neutral mapping (case folding or a fixed English locale)."""
    opp = [e for e in edits[sha] if e["direction"] == "LINGUISTIC_REPAIR"]
    return bool(opp) and all(FOLD.search(e["added"]) or ENGLISH.search(e["added"]) for e in opp)
cat = collections.Counter(); items = collections.defaultdict(list)
for i in g:
    sha = key[i]["sha"]; ds = sorted({e["direction"] for e in edits[sha]}); role = adj[i]["role"]
    if ds == ["LINGUISTIC_REPAIR"] and neutral(sha):
        k = "role_neutral"
    elif ds == ["MACHINE_PINNING"]:
        k = {"MACHINE": "fit", "LINGUISTIC": "pin_on_linguistic", "MIXED": "mixed"}.get(role, "unclear")
    elif ds == ["LINGUISTIC_REPAIR"]:
        k = {"LINGUISTIC": "fit", "MACHINE": "aware_on_machine", "MIXED": "mixed"}.get(role, "unclear")
    else:
        k = "unclear"
    cat[k] += 1; items[k].append(i)
mis = cat["pin_on_linguistic"] + cat["aware_on_machine"]
out["role_fit_r3"] = {"n": len(g), **dict(cat), "misfit_combinations": mis, "misfit_wilson": wilson(mis, len(g)),
                      "items": {k: sorted(v) for k, v in items.items() if k != "fit"}}

# (c) context probes: X3 as a comparator-consistency control
DET = ROOT / "detectors" if (ROOT.parent / "full_study").exists() else ROOT.parent / "analyzers"  # study / public layout
cx = list(csv.DictReader(open(DET / "results/detector_matrix_context.csv")))
ex = [r for r in cx if r["tool"] not in ("semgrep_registry", "semgrep_prototype") and r["probe"] != "X3"]
pairs = {(r["language"], r["tool"], r["probe"]) for r in ex}
out["context_without_X3"] = {"pairs": len(pairs),
                             "cdm_flagged": sum(int(r["flagged"]) for r in ex if r["label"] == "CDM"), "cdm_cells": sum(1 for r in ex if r["label"] == "CDM"),
                             "correct_flagged": sum(int(r["flagged"]) for r in ex if r["label"] != "CDM"),
                             "prototype_pairs": len({(r["language"], r["probe"]) for r in cx if r["tool"] == "semgrep_prototype" and r["probe"] != "X3"})}

# (d) majority-class baseline for the lexical cues on the covered main sample
h = json.load(open(ROOT / "results/role_heuristic_eval.json"))["main"]
mp, mn = map(int, h["MACHINE"]["precision"].split("/")); lp, ln = map(int, h["LINGUISTIC"]["precision"].split("/"))
true_machine_covered = mp + (ln - lp)
out["heuristic_baseline"] = {"covered": h["covered"], "true_machine_covered": true_machine_covered,
                             "always_machine_accuracy": round(true_machine_covered / h["covered"], 4), "heuristic_accuracy": h["accuracy_on_covered"]}

# (e) breakdowns used in the text
exc = [i for i in key if key[i]["sample"] == "excluded" and adj[i]["genuine"] == "YES"]
out["excluded_genuine"] = {"n": len(exc), "role": dict(collections.Counter(adj[i]["role"] for i in exc)),
                           "family": dict(collections.Counter(adj[i]["family"] for i in exc))}
m = json.load(open(ROOT / "results/rq3_mining.json"))
out["env_shell_build"] = m["eco_op_commits"].get("shell_build|ENV", 0)
FS = ROOT.parent / "full_study/results/processed/controlled_observations.csv"
if not FS.exists():  # public package layout
    FS = ROOT.parent / "data/controlled/controlled_observations.csv"
obs = [r for r in csv.DictReader(open(FS)) if r["api_contract_status"] not in ("unsupported",)]
f6 = [r for r in obs if r["scenario_family"].startswith("F6")]
out["f6_cells"] = {"n": len(f6), "contract_status": dict(collections.Counter(r["api_contract_status"] for r in f6))}

json.dump(out, open(ROOT / "results/r3_audit.json", "w"), indent=1, ensure_ascii=False)
print(json.dumps(out, indent=1, ensure_ascii=False))
