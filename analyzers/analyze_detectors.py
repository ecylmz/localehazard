"""RQ4: build the probe x detector verdict matrix from raw tool outputs (locale-relevant rules only)."""
import csv, json, re, glob, pathlib, xml.etree.ElementTree as ET
H = pathlib.Path(__file__).resolve().parent
_PJ = json.load(open(H / "probes.json")); SPEC = _PJ["probes"]; OVR = _PJ.get("overrides", {})
# Locale-relevant rules: rules whose documentation concerns locale, culture, case conversion, or collation (fixed before parsing).
RELEVANT = {
 "errorprone": {"StringCaseLocaleUsage", "DefaultLocale"},
 "spotbugs": {"DM_CONVERT_CASE"},
 "pmd": {"UseLocaleWithCaseConversions"},
 "forbiddenapis": {"Uses default locale"},
 "dotnet": {"CA1304", "CA1305", "CA1307", "CA1308", "CA1309", "CA1310", "CA1311", "CA1862"},
}
hits = {}  # (lang, tool, probe, role) -> set(rules)
allrules = {}
def add(lang, tool, fname, rule):
    m = re.search(r"([PpXx])([1-5])_(machine|linguistic)", fname)
    if not m: return
    k = (lang, tool, m.group(1).upper() + m.group(2), m.group(3))
    allrules.setdefault((lang, tool), set()).add(rule)
    if rule in RELEVANT.get(tool, set()):
        hits.setdefault(k, set()).add(rule)
for l in open(H / "java/out/errorprone.txt"):
    m = re.search(r"probes/([PX]\d_\w+)\.java:\[\d+,\d+\] \[(\w+)\]", l)
    if m: add("java", "errorprone", m.group(1), m.group(2))
for b in ET.parse(H / "java/out/spotbugsXml.xml").getroot().iter("BugInstance"):
    add("java", "spotbugs", b.find("Class").get("classname"), b.get("type"))
r = ET.parse(H / "java/out/pmd.xml").getroot(); ns = {"p": r.tag.split("}")[0][1:]}
for f in r.findall("p:file", ns):
    for v in f.findall("p:violation", ns): add("java", "pmd", f.get("name"), v.get("rule"))
lines = open(H / "java/out/forbidden.txt").read().splitlines()
for i, l in enumerate(lines):
    if "Forbidden method invocation" in l:
        m = re.search(r"in probes\.([PX]\d_\w+)", lines[i + 1])
        sig = re.findall(r"\[([^\]]*)\]", l)[-1]
        if m: add("java", "forbiddenapis", m.group(1), sig)
for l in open(H / "dotnet/out/build.txt"):
    m = re.search(r"([PX]\d_\w+)\.cs\(\d+,\d+\): warning (CA\d+|IDE\d+|CS\d+)", l)
    if m: add("dotnet", "dotnet", m.group(1), m.group(2))
for tool, fn, rx in [("staticcheck", "go/out/staticcheck.txt", r"(p\d_\w+)\.go:\d+:\d+: .*\((\w+)\)"),
                     ("govet", "go/out/vet.txt", r"(p\d_\w+)\.go:\d+:\d+: (.*)"),
                     ("ruff", "python/out/ruff.txt", r"(p\d_\w+)\.py:\d+:\d+: (\w+)"),
                     ("pylint", "python/out/pylint.txt", r"(p\d_\w+)\.py:\d+:\d+: (\w+)"),
                     ("clang-tidy", "c/out/clang-tidy.txt", r"(p\d_\w+)\.c:\d+:\d+: warning: .*\[([^\]]+)\]"),
                     ("cppcheck", "c/out/cppcheck.txt", r"(p\d_\w+)\.c:\d+:(\w+)")]:
    lang = {"staticcheck": "go", "govet": "go", "ruff": "python", "pylint": "python", "clang-tidy": "c", "cppcheck": "c"}[tool]
    for l in open(H / fn):
        m = re.search(rx, l)
        if m: add(lang, tool, m.group(1), m.group(2))
for f in json.load(open(H / "js/out/eslint.json")):
    for m in f["messages"]: add("js", "eslint", f["filePath"].split("/")[-1], m["ruleId"] or "")
TOOLS = {"java": ["errorprone", "spotbugs", "pmd", "forbiddenapis"], "dotnet": ["dotnet"], "go": ["govet", "staticcheck"],
         "python": ["ruff", "pylint"], "js": ["eslint"], "c": ["clang-tidy", "cppcheck"]}
AVAIL = {"java": ["P1", "P2", "P3", "P4", "P5"], "dotnet": ["P1", "P2", "P3", "P4", "P5"], "go": ["P2", "P3", "P4", "P5"],
         "python": ["P3", "P5"], "js": ["P1", "P2", "P3", "P4", "P5"], "c": ["P1", "P2", "P3", "P4", "P5"]}
dyn = {}
for f in glob.glob(str(H / "dyn_*.tsv")):
    for l in open(f):
        p = l.strip().split("\t")
        if len(p) == 4: dyn[(p[0], p[1], p[2])] = p[3]
rows = []
for lang, tools in TOOLS.items():
    for t in tools:
        for p in AVAIL[lang]:
            for role in ("machine", "linguistic"):
                rules = sorted(hits.get((lang, t, p, role), []))
                rows.append({"language": lang, "tool": t, "probe": p, "role": role, "label": OVR.get(lang, {}).get(p, {}).get(role, SPEC[p][role]),
                             "dynamic_outcome": dyn.get((lang, p, role), "NOT_EXECUTED"),
                             "flagged": int(bool(rules)), "locale_rules": ";".join(rules)})
out = H / "results"; out.mkdir(exist_ok=True)
with open(out / "detector_matrix.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
summ = {}
for lang, tools in TOOLS.items():
    for t in tools:
        R = [r for r in rows if r["tool"] == t and r["language"] == lang]
        pairs = {}
        for r in R: pairs.setdefault(r["probe"], {})[r["role"]] = r["flagged"]
        cdm = [r for r in R if r["label"] == "CDM"]; ok = [r for r in R if r["label"] == "CORRECT"]
        summ[f"{lang}/{t}"] = {"probe_pairs": len(pairs), "pairs_with_different_verdicts": sum(1 for v in pairs.values() if v["machine"] != v["linguistic"]),
            "cdm_cells": len(cdm), "cdm_flagged": sum(r["flagged"] for r in cdm), "correct_cells": len(ok), "correct_flagged": sum(r["flagged"] for r in ok),
            "all_rules_reported": sorted(allrules.get((lang, t), []))}
tot = {"cdm_cells": sum(1 for r in rows if r["label"] == "CDM"), "cdm_flagged": sum(r["flagged"] for r in rows if r["label"] == "CDM"),
       "correct_cells": sum(1 for r in rows if r["label"] == "CORRECT"), "correct_flagged": sum(r["flagged"] for r in rows if r["label"] == "CORRECT"),
       "tool_pairs": sum(v["probe_pairs"] for v in summ.values()), "tool_pairs_role_discriminating": sum(v["pairs_with_different_verdicts"] for v in summ.values()),
       "label_vs_dynamic_disagreements": [(r["language"], r["probe"], r["role"], r["label"], r["dynamic_outcome"]) for r in rows if r["tool"] == TOOLS[r["language"]][0] and r["dynamic_outcome"] not in ("NOT_EXECUTED", r["label"])]}
# context-bearing probes (Java, .NET) and Semgrep
CTX = _PJ["context_probes"]
sg = json.load(open(H / "semgrep/semgrep.json")); sgp = json.load(open(H / "semgrep/prototype.json"))
ctx_rows = []
for lang, tools in (("java", ["errorprone", "spotbugs", "pmd", "forbiddenapis"]), ("dotnet", ["dotnet"])):
    for t in tools + ["semgrep_registry", "semgrep_prototype"]:
        for p in ("X1", "X2", "X3", "X4"):
            for role in ("machine", "linguistic"):
                if t.startswith("semgrep"):
                    res = sg if t == "semgrep_registry" else sgp
                    ext = ".java" if lang == "java" else ".cs"
                    fl = int(any(r["path"].endswith(f"{p}_{role}{ext}") for r in res["results"]))
                else:
                    fl = int(bool(hits.get((lang, t, p, role))))
                ctx_rows.append({"language": lang, "tool": t, "probe": p, "role": role, "label": CTX[p][role], "flagged": fl})
with open(out / "detector_matrix_context.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(ctx_rows[0])); w.writeheader(); w.writerows(ctx_rows)
def ctxsum(rows):
    pairs = {}
    for r in rows: pairs.setdefault((r["language"], r["tool"], r["probe"]), {})[r["role"]] = r["flagged"]
    return {"pairs": len(pairs), "discriminating": sum(1 for v in pairs.values() if v["machine"] != v["linguistic"]),
            "cdm_flagged": sum(r["flagged"] for r in rows if r["label"] == "CDM"), "cdm_cells": sum(1 for r in rows if r["label"] == "CDM"),
            "correct_flagged": sum(r["flagged"] for r in rows if r["label"] == "CORRECT"), "correct_cells": sum(1 for r in rows if r["label"] == "CORRECT")}
tot["context_existing_tools"] = ctxsum([r for r in ctx_rows if not r["tool"].startswith("semgrep")])
tot["context_semgrep_registry"] = ctxsum([r for r in ctx_rows if r["tool"] == "semgrep_registry"]) | {"rules": 719}
tot["context_semgrep_prototype"] = ctxsum([r for r in ctx_rows if r["tool"] == "semgrep_prototype"])
tot["semgrep_registry_findings_all_probes"] = len(sg["results"])
tot["tools_with_locale_rules"] = sorted(f"{l}/{t}" for (l, t) in [(r["language"], r["tool"]) for r in rows] if any(x["flagged"] for x in rows if x["tool"] == t and x["language"] == l))
tot["tools_with_locale_rules"] = sorted(set(tot["tools_with_locale_rules"]))
json.dump({"per_tool": summ, "total": tot}, open(out / "detector_summary.json", "w"), indent=1)
print(json.dumps(tot, indent=1))
for k, v in summ.items(): print(k, {x: v[x] for x in v if x != "all_rules_reported"})
