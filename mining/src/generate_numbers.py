"""Generate manuscript/numbers.tex and result tables from authoritative result files only."""
import csv, json, pathlib, re, collections

ROOT = pathlib.Path(__file__).resolve().parents[1]
# Two layouts (round 4). Study: study2/ next to full_study/. Public package: this directory is mining/, and the
# controlled benchmark, dbms/ and analyzers/ sit in the repository root; run `localehazard-analyze --check` first.
STUDY = (ROOT.parent / "full_study").exists()
if STUDY:
    FS = ROOT.parent / "full_study/results"
    M = ROOT / "manuscript"
    DB, DET = ROOT / "dbms", ROOT / "detectors"
    PATH = {"obs": FS / "processed/controlled_observations.csv", "std": FS / "processed/standards_validation.csv",
            "dom": FS / "analysis/rq2_by_text_domain.csv", "fam": FS / "analysis/rq2_by_scenario_family.csv",
            "contracts": FS.parent / "data/contracts/api_contracts.csv", "scenarios": FS.parent / "protocol/scenarios.json"}
else:
    REPO = ROOT.parent
    M = REPO / "numbers"; M.mkdir(exist_ok=True)
    DB, DET = REPO / "dbms", REPO / "analyzers"
    PATH = {"obs": REPO / "data/controlled/controlled_observations.csv", "std": REPO / "data/controlled/standards_validation.csv",
            "dom": REPO / "out/analysis/controlled_by_text_domain.csv", "fam": REPO / "out/analysis/controlled_by_scenario_family.csv",
            "contracts": REPO / "contracts/api_contracts.csv", "scenarios": REPO / "scenarios/cases.json"}


def final_numbers():
    if STUDY:
        return json.load(open(FS / "analysis/final_numbers.json"))
    s = json.load(open(REPO / "out/analysis/summary.json"))
    o = s["controlled_outcomes"]
    return {"controlled_observations": s["study_surface"]["controlled_observations"], "unique_failure_signatures": o["unique_failure_signatures"],
            "outcomes": {"application_correct": o["application_correct"], "cdm_hazard": o["cdm_hazard"], "unsupported": o["unsupported"]}}
N = {}


def fmt(x):
    return f"{x:,}" if isinstance(x, int) else str(x)


def pct(a, b, d=1):
    return f"{100 * a / b:.{d}f}"


# ---------- RQ1 (frozen) ----------
fn = final_numbers()
obs = list(csv.DictReader(open(PATH["obs"])))
N.update(RoneObs=fn["controlled_observations"], RoneSupp=fn["outcomes"]["application_correct"] + fn["outcomes"]["cdm_hazard"],
         RoneUnsup=fn["outcomes"]["unsupported"], RoneCorrect=fn["outcomes"]["application_correct"], RoneCDM=fn["outcomes"]["cdm_hazard"],
         RoneSig=fn["unique_failure_signatures"], RoneAPIs=len(list(csv.DictReader(open(PATH["contracts"])))), RoneCases=len(json.load(open(PATH["scenarios"]))))
assert len(obs) == N["RoneObs"]
f6 = [r for r in obs if r["scenario_family"].startswith("F6") and r["api_contract_status"] == "conformant"]
N.update(RoneProvCells=len(f6), RoneProvUnspec=sum(1 for r in f6 if r["expected_contract"] == "no_cross_provider_stability_promise"))  # round-3 audit
dom = {r["text_domain"]: r for r in csv.DictReader(open(PATH["dom"]))}
mach = ["machine_token_or_keyword", "identifier_or_opaque_key", "application_defined_canonical_text"]
N["RoneMachCDM"] = sum(int(dom[d]["cdm_hazards"]) for d in mach)
N["RoneMachSupp"] = sum(int(dom[d]["eligible"]) for d in mach)
N["RoneLingCDM"] = int(dom["linguistic_user_text"]["cdm_hazards"]); N["RoneLingSupp"] = int(dom["linguistic_user_text"]["eligible"])
N["RonePersCDM"] = int(dom["persisted_collated_text"]["cdm_hazards"]); N["RonePersSupp"] = int(dom["persisted_collated_text"]["eligible"])
sv = list(csv.DictReader(open(PATH["std"])))
N["RoneStd"] = len(sv); N["RoneStdApp"] = sum(1 for r in sv if r["standards_oracle_status"] == "conformant")
assert all(r["standards_oracle_status"] in ("conformant", "not_applicable") for r in sv)
fam = list(csv.DictReader(open(PATH["fam"])))
names = {"F1": "F1 linguistic tailored mapping", "F2": "F2 machine/canonical mapping", "F3": "F3 comparison semantics",
         "F4": "F4 normalization interaction", "F5": "F5 native process-locale", "F6": "F6 provider-relation portability", "F7": "F7 neutral controls"}
rows = []
for r in fam:
    k = r["scenario_family"][:2]
    rows.append(f"{names[k]} & {r['observations']} & {r['eligible']} & {r['unsupported']} & {r['cdm_hazards']} \\\\")
tot = [sum(int(r[c]) for r in fam) for c in ("observations", "eligible", "unsupported", "cdm_hazards")]
assert tot == [N["RoneObs"], N["RoneSupp"], N["RoneUnsup"], N["RoneCDM"]], tot
(M / "tab_rq1.tex").write_text("\\begin{table}[t]\n\\centering\n\\small\n\\caption{Controlled demonstration by scenario family. All supported executions conformed to their API contracts; CDM counts are judged by the application oracle and follow from the design, so they are not prevalence estimates.}\n\\label{tab:rq1}\n"
    "\\begin{tabular}{@{}lrrrr@{}}\n\\toprule\nScenario family & Planned & Supported & Unsupported & CDM \\\\\n\\midrule\n" + "\n".join(rows) +
    f"\n\\midrule\nTotal & {tot[0]} & {tot[1]} & {tot[2]} & {tot[3]} \\\\\n\\bottomrule\n\\end{{tabular}}\n\\end{{table}}\n")

# ---------- RQ2 (DBMS; reported as RQ3 in the manuscript) ----------
import random
D = {k: json.load(open(DB / f"results/dbms_results_{k}.json")) for k in ("synthetic", "dictionary")}
SEP = re.compile(r"[ \-_./']")
for k, tag in (("synthetic", "Syn"), ("dictionary", "Dic")):
    rows_n = D[k]["meta"]["rows"]
    rows = [r[1] for r in csv.reader(open(DB / f"results/raw_{k}/dataset.csv"))]
    keys = random.Random(20261001 + 1).sample(rows, 20000)
    d = D[k]["drift"]["libc_en"]
    miss = d["seq_point_hits"] - d["index_point_hits"]
    assert miss == len(d["missed_keys"]), (miss, len(d["missed_keys"]))
    ms = set(d["missed_keys"])
    plain = [x for x in keys if not SEP.search(x)]; sep = [x for x in keys if SEP.search(x)]
    N[f"Rtwo{tag}Rows"] = rows_n; N[f"Rtwo{tag}Miss"] = miss; N[f"Rtwo{tag}MissPct"] = pct(miss, d["lookups"])
    N[f"Rtwo{tag}RangeBad"] = d["range_count_mismatches"]; N[f"Rtwo{tag}NonEmpty"] = d["nonempty_ranges"]
    N[f"Rtwo{tag}RangePctNE"] = pct(d["range_count_mismatches"], d["nonempty_ranges"])
    N[f"Rtwo{tag}Dup"] = d["reinserted_existing_keys_accepted"]; N[f"Rtwo{tag}DupPct"] = pct(d["reinserted_existing_keys_accepted"], rows_n)
    N[f"Rtwo{tag}PlainMissPct"] = pct(sum(x in ms for x in plain), len(plain)); N[f"Rtwo{tag}SepMissPct"] = pct(sum(x in ms for x in sep), len(sep))
    sd = D[k]["silent"]["libc_en"]
    N[f"Rtwo{tag}SilentMissPct"] = pct(sd["seq_point_hits"] - sd["index_point_hits"], sd["lookups"]); N[f"Rtwo{tag}SilentDup"] = sd["reinserted_existing_keys_accepted"]
    assert sd["connect_warning"] is False and d["connect_warning"] is True and D[k]["drift228"]["libc_en"]["connect_warning"] is True
    N["RtwoLookups"] = d["lookups"]; N["RtwoRanges"] = d["ranges"]
    for c in ("drift", "drift228", "silent", "stable"):
        for db, v in D[k][c].items():
            if db.startswith("_"):
                continue
            assert v["remediated_clone_amcheck_ok"] and v["remediated_clone_missed"] == 0 and v["remediated_clone_range_mismatches"] == 0, (k, c, db)
            if db == "libc_en" and c != "stable":
                continue
            assert v["amcheck_bt_index_check_ok"] and v["amcheck_parent_check_ok"] and v["range_count_mismatches"] == 0 \
                and v["index_point_hits"] == v["seq_point_hits"] and v["reinserted_existing_keys_accepted"] == 0, (k, c, db)
N["RtwoSilentMissPct"] = N["RtwoSynSilentMissPct"]; N["RtwoSilentDup"] = N["RtwoSynSilentDup"]
dic_rows = [r[1] for r in csv.reader(open(DB / "results/raw_dictionary/dataset.csv"))]
N["RtwoDicApos"] = f"{100 * sum(chr(39) in s for s in dic_rows) / len(dic_rows):.0f}"
em = json.load(open(DB / "results/emulation/emulation_check.json"))
assert all(em[x]["real227_equals_emulated227"] and em[x]["positions_differing_228_vs_243"] == 0 for x in em)
N["RtwoEmulN"] = sum(em[x]["n"] for x in em); N["RtwoEmulSynDiff"] = em["synthetic"]["positions_differing_real227_vs_243"]
N["RtwoEmulDicDiff"] = em["dictionary"]["positions_differing_real227_vs_243"]
COND = [("drift", "2.27$\\to$2.43, 2.43 reported"), ("drift228", "2.27$\\to$2.28, 2.28 reported"),
        ("silent", "2.27$\\to$2.43, 2.27 reported"), ("stable", "unchanged 2.27")]
def rq2row(label, v):
    miss = v["seq_point_hits"] - v["index_point_hits"]
    am = "pass" if v["amcheck_bt_index_check_ok"] and v["amcheck_parent_check_ok"] else "\\textbf{fail}"
    return f"{label} & {am} & {fmt(miss)} & {fmt(v['range_count_mismatches'])}/{fmt(v['nonempty_ranges'])} & {fmt(v['reinserted_existing_keys_accepted'])} & {'yes' if v['connect_warning'] else 'no'} \\\\"
lines = []
for k, kl in (("synthetic", f"Synthetic keys ({fmt(D['synthetic']['meta']['rows'])} rows)"), ("dictionary", f"English word list ({fmt(D['dictionary']['meta']['rows'])} rows)")):
    lines.append(f"\\multicolumn{{6}}{{@{{}}l}}{{\\emph{{{kl}}}}} \\\\")
    for c, cl in COND:
        lines.append(rq2row(f"\\quad libc, {cl}", D[k][c]["libc_en"]))
    for db, dl in (("icu_en", "ICU \\code{en}"), ("c_coll", "\\code{C} collation")):
        lines.append(rq2row(f"\\quad {dl}, 2.27$\\to$2.43", D[k]["drift"][db]))
(M / "tab_rq2.tex").write_text("\\begin{table}[t]\n\\centering\n\\footnotesize\n\\caption{RQ3: B-tree integrity in PostgreSQL~18.6 after restarting a cluster indexed under glibc~2.27 collation data; each row gives the collation data used after the restart and the glibc version PostgreSQL saw. Missed lookups are among "
    + fmt(N["RtwoLookups"]) + " existing keys; wrong ranges are counts that differ from a sequential scan, among the non-empty range queries; duplicates are re-inserted existing keys accepted by the \\code{UNIQUE} index; the last column is PostgreSQL's collation-version mismatch warning. ICU and \\code{C} databases, which do not use glibc collation data, were clean in every condition, and every remediated copy (\\code{REINDEX} plus \\code{REFRESH COLLATION VERSION}) was consistent.}\n\\label{tab:rq2}\n"
    "\\setlength{\\tabcolsep}{3pt}\n\\begin{tabular}{@{}lrrrrr@{}}\n\\toprule\nCondition & \\code{amcheck} & Missed & Wrong & Duplicate & Mismatch \\\\\n & & lookups & ranges & keys & warning \\\\\n\\midrule\n" + "\n".join(lines) + "\n\\bottomrule\n\\end{tabular}\n\\end{table}\n")
T = D["synthetic"]["turkic"]
assert T["tr_libc"]["lower_FILE"] == "f\u0131le" and T["tr_icu"]["accounts_admitted"] == "2" and T["en_libc"]["accounts_admitted"] == "1" and T["tr_coll_c_ctype"]["citext_accounts_admitted"] == "2"

# ---------- RQ4 ----------
ds = json.load(open(DET / "results/detector_summary.json"))["total"]
N.update(RfourPairs=ds["tool_pairs"], RfourDisc=ds["tool_pairs_role_discriminating"], RfourCDMFlag=ds["cdm_flagged"],
         RfourCDMCells=ds["cdm_cells"], RfourOKFlag=ds["correct_flagged"], RfourOKCells=ds["correct_cells"])
assert N["RfourDisc"] == 0
dt = json.load(open(DET / "results/detector_summary.json"))["total"]
rule_tools = dt["tools_with_locale_rules"]
mx = list(csv.DictReader(open(DET / "results/detector_matrix.csv")))
rt = [r for r in mx if f"{r['language']}/{r['tool']}" in rule_tools]
N.update(RfourToolsRule=len(rule_tools), RfourToolsTotal=len({(r["language"], r["tool"]) for r in mx}),
         RfourRulePairs=len({(r["language"], r["tool"], r["probe"]) for r in rt}),
         RfourRuleCDMCells=sum(1 for r in rt if r["label"] == "CDM"), RfourRuleCDMFlag=sum(int(r["flagged"]) for r in rt if r["label"] == "CDM"),
         RfourRuleOKCells=sum(1 for r in rt if r["label"] == "CORRECT"), RfourRuleOKFlag=sum(int(r["flagged"]) for r in rt if r["label"] == "CORRECT"),
         RfourPtwoFlag=sum(int(r["flagged"]) for r in mx if r["probe"] == "P2"), RfourPtwoCells=sum(1 for r in mx if r["probe"] == "P2"),
         RfourCtxPairs=dt["context_existing_tools"]["pairs"], RfourCtxDisc=dt["context_existing_tools"]["discriminating"],
         RfourCtxCDMFlag=dt["context_existing_tools"]["cdm_flagged"], RfourCtxCDMCells=dt["context_existing_tools"]["cdm_cells"],
         RfourCtxOKFlag=dt["context_existing_tools"]["correct_flagged"], RfourSgRules=dt["context_semgrep_registry"]["rules"],
         RfourSgFindings=dt["semgrep_registry_findings_all_probes"], RfourProtoPairs=dt["context_semgrep_prototype"]["pairs"],
         RfourProtoDisc=dt["context_semgrep_prototype"]["discriminating"])

# ---------- RQ3 ----------
rq3p = ROOT / "results/rq3_numbers.json"
if rq3p.exists():
    N.update(json.load(open(rq3p)))

out = ["% generated by src/generate_numbers.py -- do not edit"]
for k, v in sorted(N.items()):
    if not re.fullmatch(r"[A-Za-z]+", k):
        raise ValueError(k)
    out.append(f"\\providecommand{{\\{k}}}{{{fmt(v) if not isinstance(v, str) else v}}}")
(M / "numbers.tex").write_text("\n".join(out) + "\n")
print(len(N), "macros")
