"""Convert RQ3 result files into manuscript macros (results/rq3_numbers.json)."""
import csv, json, pathlib, statistics

ROOT = pathlib.Path(__file__).resolve().parents[1]
m = json.load(open(ROOT / "results/rq3_mining.json"))
f = m["funnel"]; s = m["shares"]
pc = lambda x: f"{100 * x:.1f}"
ci = lambda d: f"{100 * d['ci95'][0]:.1f}--{100 * d['ci95'][1]:.1f}\\%"
N = {
    "RthreeQueries": f["queries"], "RthreeReportedTotal": sum(f["reported_total_counts"].values()), "RthreeSearchHits": f["search_hits"],
    "RthreeUnique": f["unique_nonmerge_commits"], "RthreeFetched": f["fetched_ok"], "RthreeIncluded": f["included_after_vendored_exclusion"],
    "RthreeFormatOnly": f["format_only"], "RthreeLineages": f["lineages"], "RthreeCollapsed": f["commits_collapsed_by_lineage"],
    "RthreeRepos": f["repositories"], "RthreeEdits": f["repair_edits_in_lineages"],
    "RthreeSitesMedian": int(m["sites_per_commit"]["median"]), "RthreeSitesPninety": m["sites_per_commit"]["p90"],
    "RthreeSingleSite": pc(m["sites_per_commit"]["single_site_share"]),
    "RthreeMultiRepos": m["repos_with_multiple_lineages"], "RthreeMultiShare": pc(m["multi_lineage_repo_share"]),
    "RthreeMultiLineages": m["lineages_in_multi_repos"], "RthreeGapDays": m["gap_days_multi_repos"]["median"],
    "RthreeStarLineages": m["stars_ge_10"]["lineages"], "RthreeStarRepos": m["stars_ge_10"]["repos"],
}
for key, mac in (("machine_pinning_only", "Pin"), ("any_linguistic_repair", "Ling"), ("msg_turkic", "Turk"), ("msg_failure", "Fail"),
                 ("msg_analyzer", "Analyzer"), ("test_change", "Test"), ("msg_issue_ref", "Issue"), ("msg_bot", "Bot")):
    N[f"Rthree{mac}Share"] = pc(s[key]["share"]); N[f"Rthree{mac}CI"] = ci(s[key]); N[f"Rthree{mac}K"] = s[key]["k"]
if m.get("shares_turkic_subset"):
    N["RthreeTurkTestShare"] = pc(m["shares_turkic_subset"]["test_change"]["share"]); N["RthreeTurkTestCI"] = ci(m["shares_turkic_subset"]["test_change"])
st = m["stars_ge_10"]
if st.get("test_change"):
    N["RthreeStarTestShare"] = pc(st["test_change"]["share"]); N["RthreeStarTurkShare"] = pc(st["msg_turkic"]["share"])
ai = m["post_hoc_ai_agent"]
N.update(RthreeAIK=ai["lineages_with_trailer"]["k"], RthreeAIShare=pc(ai["lineages_with_trailer"]["share"]),
         RthreeAITwentySix=ai["by_year"].get("2026", 0), RthreeAITwentyFive=ai["by_year"].get("2025", 0),
         RthreeYearTwentySix=m["year_lineages"].get("2026", 0), RthreeYearTwentyFive=m["year_lineages"].get("2025", 0),
         RthreeYearMaxPre=max(v for y, v in m["year_lineages"].items() if y < "2025"),
         RthreeAITestShare=pc(ai["with_trailer_test_change"]["share"]), RthreeAITestCI=ci(ai["with_trailer_test_change"]),
         RthreePreTestShare=pc(ai["before_2025"]["test_change"]["share"]), RthreePreTestCI=ci(ai["before_2025"]["test_change"]),
         RthreePreN=ai["before_2025"]["test_change"]["n"], RthreePrePinShare=pc(ai["before_2025"]["machine_pinning_only"]["share"]),
         RthreePreTurkShare=pc(ai["before_2025"]["msg_turkic"]["share"]),
         RthreeNoAITestShare=pc(ai["without_trailer"]["test_change"]["share"]), RthreeNoAIPinShare=pc(ai["without_trailer"]["machine_pinning_only"]["share"]))
eco = m["ecosystem_commits"]; N.update({f"RthreeEco{k.replace('_', '').replace('cpp', 'Cpp').capitalize()}": v for k, v in eco.items()})
ops = m["op_commits"]; N.update({f"RthreeOp{k.capitalize()}": v for k, v in ops.items()})
v = ROOT / "results/rq3_validation.json"
if v.exists():
    V = json.load(open(v))
    N.update(RthreeValItems=V["items"], RthreeValN=V["precision"]["n"], RthreePrecK=V["precision"]["k"], RthreePrec=pc(V["precision"]["share"]),
             RthreePrecCI=f"{100 * V['precision']['wilson95'][0]:.1f}--{100 * V['precision']['wilson95'][1]:.1f}\\%",
             RthreeNegN=V["excluded_genuine"]["n"], RthreeNegK=V["excluded_genuine"]["k"],
             RthreeKappaGen=V["agreement"]["genuine"]["kappa"], RthreeKappaRole=V["agreement"]["role"]["kappa"],
             RthreeKappaTrig=V["agreement"]["trigger"]["kappa"], RthreeKappaFam=V["agreement"]["family"]["kappa"],
             RthreeRawGen=pc(V["agreement"]["genuine"]["raw"]), RthreeRawRole=pc(V["agreement"]["role"]["raw"]),
             RthreeRawTrig=pc(V["agreement"]["trigger"]["raw"]), RthreeRawFam=pc(V["agreement"]["family"]["raw"]),
             RthreeValGenuine=V["precision"]["k"], RthreeValMachine=V["role_genuine_included"].get("MACHINE", 0),
             RthreeValLing=V["role_genuine_included"].get("LINGUISTIC", 0), RthreeValMixed=V["role_genuine_included"].get("MIXED", 0),
             RthreeValRoleUnclear=V["role_genuine_included"].get("UNCLEAR", 0),
             RthreeTrigFail=V["trigger_genuine_included"].get("OBSERVED_FAILURE", 0), RthreeTrigTool=V["trigger_genuine_included"].get("TOOL_DRIVEN", 0),
             RthreeTrigPrev=V["trigger_genuine_included"].get("PREVENTIVE", 0), RthreeTrigUnclear=V["trigger_genuine_included"].get("UNCLEAR", 0))
    for fam, n in V["family_genuine_included"].items():
        w = {"1": "One", "2": "Two", "3": "Three", "4": "Four", "5": "Five", "6": "Six", "7": "Seven"}
        N["RthreeFam" + "".join(w.get(ch, ch) for ch in fam.capitalize() if ch.isalnum())] = n
lr = ROOT / "results/rq3_ling_roles.json"
if lr.exists():
    G = json.load(open(lr)); la = G["locale_aware_machine_or_mixed"]
    N.update(RthreeLingN=G["n"], RthreeLingKappa=G["kappa_role"], RthreeLingLA=la["n"], RthreeLingLAMach=la["k"], RthreeLingLAShare=pc(la["share"]),
             RthreeLingLACI=f"{100 * la['wilson95'][0]:.1f}--{100 * la['wilson95'][1]:.1f}\\%", RthreeLingFold=G["final"]["change"].get("UNICODE_FOLD", 0),
             RthreeLingLALing=G["role_by_change"]["LOCALE_AWARE"].get("LINGUISTIC", 0))
if v.exists():
    N["RthreeNegShare"] = pc(V["excluded_genuine"]["share"]); N["RthreeNegCI"] = f"{100 * V['excluded_genuine']['wilson95'][0]:.1f}--{100 * V['excluded_genuine']['wilson95'][1]:.1f}\\%"
    N["RthreeNegLing"] = V["role_genuine_excluded"].get("LINGUISTIC", 0); N["RthreeNegFamOne"] = V["family_genuine_excluded"].get("F1", 0)
    N["RthreeValMachineShare"] = pc(V["role_genuine_included"].get("MACHINE", 0) / V["precision"]["k"])
r = ROOT / "data/processed/residual_sites.csv"
if r.exists():
    rows = [x for x in csv.DictReader(open(r)) if x["fetched"] == "1"]
    by = {}
    for x in rows:
        by.setdefault(x["sha"], 0); by[x["sha"]] += int(x["residual_calls"])
    N["RthreeResidN"] = len(by); N["RthreeResidFiles"] = len(rows)
    N["RthreeResidAny"] = sum(1 for c in by.values() if c > 0); N["RthreeResidAnyShare"] = pc(N["RthreeResidAny"] / len(by))
    N["RthreeResidFileAny"] = pc(sum(1 for x in rows if int(x["residual_calls"]) > 0) / len(rows))
    N["RthreeResidMedianPos"] = statistics.median([c for c in by.values() if c > 0]) if N["RthreeResidAny"] else 0
json.dump(N, open(ROOT / "results/rq3_numbers.json", "w"), indent=1)
print(json.dumps(N, indent=1))

# ---- post-review additions ----
pr = ROOT / "results/rq3_post_review.json"
if pr.exists():
    R = json.load(open(pr)); W = lambda w: f"{100 * w[0]:.1f}--{100 * w[1]:.1f}\\%"
    p2 = R["precision_v2"]; rc = R["recall_turkic_subframe"]; rs = R["role_consistency_summ" + "ary"]; ta = R["towards_aware_machine_items"]; ag = R["agents"]
    N.update(RthreePrecVtwo=pc(p2["share"]), RthreePrecVtwoCI=W(p2["wilson95"]), RthreePrecVtwoK=p2["k"], RthreePrecVtwoN=p2["n"],
             RthreeDroppedVtwo=p2["dropped_by_v2"], RthreeDroppedGenuine=p2["dropped_genuine"],
             RthreeRecall=f"{100 * rc['estimate']:.0f}", RthreeRecallLo=f"{100 * rc['bounds'][0]:.0f}", RthreeRecallHi=f"{100 * rc['bounds'][1]:.0f}",
             RthreeRecallInc=rc["included"], RthreeRecallExc=rc["excluded_nonformat"],
             RthreeTurkNoT=pc(R["turkic_share_excluding_T_queries"]["share"]), RthreeTurkNoTCI=ci(R["turkic_share_excluding_T_queries"]),
             RthreeAnalyzerNoA=pc(R["analyzer_share_excluding_A_queries"]["share"]), RthreeAnalyzerNoACI=ci(R["analyzer_share_excluding_A_queries"]),
             RthreePinNonPinQ=pc(R["pinning_only_excluding_pinning_queries"]["share"]), RthreePinNonPinQCI=ci(R["pinning_only_excluding_pinning_queries"]),
             RthreeNonPinQN=R["pinning_only_excluding_pinning_queries"]["n"],
             RthreeLocTest=pc(R["locale_relevant_test"]["share"]), RthreeLocTestCI=ci(R["locale_relevant_test"]), RthreeLocTestK=R["locale_relevant_test"]["k"],
             RthreeLocTestTurk=pc(R["locale_relevant_test_turkic_msg"]["share"]), RthreeLocTestTurkCI=ci(R["locale_relevant_test_turkic_msg"]),
             RthreeAgentTest=pc(ag["agent_test"]["share"]), RthreeAgentTestCI=ci(ag["agent_test"]), RthreeContempTest=pc(ag["nonagent_2025_26_test"]["share"]),
             RthreeContempTestCI=ci(ag["nonagent_2025_26_test"]), RthreeAgentLocTest=pc(ag["agent_loctest"]["share"]), RthreeAgentLocTestCI=ci(ag["agent_loctest"]),
             RthreeContempLocTest=pc(ag["nonagent_2025_26_loctest"]["share"]), RthreeContempLocTestCI=ci(ag["nonagent_2025_26_loctest"]),
             RthreeAgentN=ag["agent_test"]["n"], RthreeContempN=ag["nonagent_2025_26_test"]["n"],
             RthreeFetchedTwentySix=pc(ag["fetched_2026_share"]),
             RthreeMultiSameDay=R["multi_repos"]["within_1_day"], RthreeMultiWeek=R["multi_repos"]["within_7_days"],
             RthreeConsN=rs["n"], RthreeConsistent=rs["consistent"], RthreeIntroduces=rs["introduces_cdm"], RthreeIntroducesCI=W(rs["introduces_wilson"]),
             RthreeConsMixed=rs["mixed"], RthreePinTotal=rs["pinning_total"], RthreePinOnLingMixed=rs["pinning_on_linguistic_or_mixed"],
             RthreePinOnLing=R["role_consistency_coded"].get("pinning_on_LINGUISTIC", 0), RthreeAwareOnMachine=R["role_consistency_coded"].get("towards_aware_on_MACHINE", 0),
             RthreeTaN=ta["n"], RthreeTaJs=ta["ecosystem"].get("js", 0), RthreeTaJsNoArg=ta["js_no_argument"], RthreeTaEnglish=ta["target"].get("explicit_english", 0),
             RthreeTaTurkic=ta["target"].get("explicit_turkic", 0), RthreeTaVariable=ta["target"].get("variable_or_culture_parameter", 0),
             RthreeLineagesWithinRepo=R["lineages_if_fingerprint_within_repo"],
             RthreeTrigPrevV=R["trigger_v2"].get("PREVENTIVE", 0), RthreeTrigFailV=R["trigger_v2"].get("OBSERVED_FAILURE", 0),
             RthreeTrigToolV=R["trigger_v2"].get("TOOL_DRIVEN", 0), RthreeTrigUnclearV=R["trigger_v2"].get("UNCLEAR", 0),
             RthreeConsUnclear=rs["unclear_or_other"])
he = ROOT / "results/role_heuristic_eval.json"
if he.exists():
    Hh = json.load(open(he))["all"]
    N.update(RthreeHeurN=Hh["n"], RthreeHeurCov=pc(Hh["coverage"]), RthreeHeurAcc=pc(Hh["accuracy_on_covered"]),
             RthreeHeurMachP=Hh["MACHINE"]["precision"].replace("/", " of "), RthreeHeurLingR=Hh["LINGUISTIC"]["recall"].replace("/", " of "))
v1 = ROOT / "results/rq3_mining_v1.json"
if v1.exists():
    m1 = json.load(open(v1))
    N.update(RthreeVoneLineages=m1["funnel"]["lineages"], RthreeVonePin=pc(m1["shares"]["machine_pinning_only"]["share"]), RthreeVoneTest=pc(m1["shares"]["test_change"]["share"]))
json.dump(N, open(ROOT / "results/rq3_numbers.json", "w"), indent=1)

r2 = ROOT / "results/rq3_round2.json"
if r2.exists():
    Z = json.load(open(r2))
    N.update(RthreeMultiOther=Z["non_same_day_multi"], RthreeGapOther=int(Z["median_gap_non_same_day"]),
             RthreeAgentDiff=f"{100 * Z['agent_test_diff'][0]:.1f}", RthreeAgentDiffCI=f"{100 * Z['agent_test_diff'][1]:.1f}--{100 * Z['agent_test_diff'][2]:.1f}")
_R = json.load(open(ROOT / "results/rq3_post_review.json")); _m = _R["towards_aware_machine_only"]
N.update(RthreeTaMach=_m["k"], RthreeTaMixed=_m["mixed"], RthreeTaMachShare=pc(_m["share"]),
         RthreeTaMachCI=f"{100 * _m['wilson95'][0]:.1f}--{100 * _m['wilson95'][1]:.1f}\\%", RthreeTaRealised=_m["realised_any_input"],
         RthreeTaMachNoArg=_m["no_argument"], RthreeTaMachEnglish=_m["english"],
         RthreeRulesPin=_R["rule_directions"]["MACHINE_PINNING"], RthreeRulesOpp=_R["rule_directions"]["LINGUISTIC_REPAIR"])
H2 = json.load(open(ROOT / "results/role_heuristic_eval.json"))
N.update(RthreeHeurMainN=H2["main"]["n"], RthreeHeurMainCov=pc(H2["main"]["coverage"]), RthreeHeurMainAcc=pc(H2["main"]["accuracy_on_covered"]),
         RthreeHeurMainMachP=H2["main"]["MACHINE"]["precision"].replace("/", " of "), RthreeHeurMainLingR=H2["main"]["LINGUISTIC"]["recall"].replace("/", " of "),
         RthreeHeurOppN=H2["towards_aware"]["n"], RthreeHeurOppCov=pc(H2["towards_aware"]["coverage"]), RthreeHeurOppAcc=pc(H2["towards_aware"]["accuracy_on_covered"]),
         RthreeHeurOppLingR=H2["towards_aware"]["LINGUISTIC"]["recall"].replace("/", " of "))
json.dump(N, open(ROOT / "results/rq3_numbers.json", "w"), indent=1)

# ---- round-3 audit additions (post hoc; src/r3_audit_analyses.py) ----
_A = ROOT / "results/r3_audit.json"
if _A.exists():
    A = json.load(open(_A)); rf = A["role_fit_r3"]; cx = A["context_without_X3"]; wr = A["within_repo"]
    N.update(RthreeFitR=rf["fit"], RthreeMisfitR=rf["misfit_combinations"], RthreeMisfitRCI=W(rf["misfit_wilson"]),
             RthreeNeutralR=rf["role_neutral"], RthreeAwareOnMachineR=rf["aware_on_machine"], RthreePinOnLingR=rf["pin_on_linguistic"],
             RthreeWRGroups=wr["groups"], RthreeWRRepos=wr["repositories"], RthreeWRPin=pc(wr["pinning_only"]["share"]), RthreeWRTest=pc(wr["test_change"]["share"]),
             RthreeReposAll=A["global"]["repositories_with_included_commits"], RthreeLeTwo=pc(A["edited_line_pairs"]["le2_share"]),
             RfourCtxPairsNoX=cx["pairs"], RfourCtxCDMFlagNoX=cx["cdm_flagged"], RfourCtxCDMCellsNoX=cx["cdm_cells"], RfourCtxOKFlagNoX=cx["correct_flagged"],
             RfourProtoPairsNoX=cx["prototype_pairs"], RthreeHeurBase=pc(A["heuristic_baseline"]["always_machine_accuracy"]),
             RthreeExcGenLing=A["excluded_genuine"]["role"].get("LINGUISTIC", 0), RthreeExcGenEnv=A["excluded_genuine"]["family"].get("F5", 0),
             RthreeOpEnvShell=A["env_shell_build"], RthreeTaMachCDM=_m["k"] - _m["english"], RthreeTaMachCDMShare=pc((_m["k"] - _m["english"]) / _m["n"]))
    json.dump(N, open(ROOT / "results/rq3_numbers.json", "w"), indent=1)

# ---- independent LLM re-coding (post hoc; src/r3_recoding.py). Cx = Codex gpt-6.1-sol (other family), Op = Claude Opus 5.5 ----
_RC = ROOT / "results/r3_recoding.json"
if _RC.exists():
    RC = json.load(open(_RC))
    for tag, src in (("Cx", "D1_codex"), ("Op", "D2_claude")):
        ag, f = RC["agreement"][f"{src}_vs_original"], RC["figures"][src]
        N.update({f"Rrc{tag}KGen": f"{ag['set1_genuine']['kappa']:.3f}", f"Rrc{tag}KRole": f"{ag['set1_role']['kappa']:.3f}", f"Rrc{tag}KTrig": f"{ag['set1_trigger']['kappa']:.3f}",
                  f"Rrc{tag}KFam": f"{ag['set1_family']['kappa']:.3f}", f"Rrc{tag}KLingRole": f"{ag['set2_role']['kappa']:.3f}", f"Rrc{tag}KLingChange": f"{ag['set2_change']['kappa']:.3f}",
                  f"Rrc{tag}PrecK": f["precision_frozen"]["k"], f"Rrc{tag}Prec": pc(f["precision_frozen"]["k"] / f["precision_frozen"]["n"]),
                  f"Rrc{tag}Misfit": f["role_fit"]["misfit"], f"Rrc{tag}MisN": f["role_fit"]["n"],
                  f"Rrc{tag}Opp": f["opposite"]["role_inconsistent"], f"Rrc{tag}OppN": f["opposite"]["locale_aware"],
                  f"Rrc{tag}OppShare": pc(f["opposite"]["role_inconsistent"] / f["opposite"]["locale_aware"]),
                  f"Rrc{tag}Recall": f"{100 * f['recall_turkic_subframe']:.0f}", f"Rrc{tag}Fail": f["trigger_v2"].get("OBSERVED_FAILURE", 0)})
    json.dump(N, open(ROOT / "results/rq3_numbers.json", "w"), indent=1)

# ---- round-4 additions (post hoc / exploratory; protocol/DEVIATIONS.md 2026-11-09). Prefix Rv = revision round 4 ----
fmt = lambda x: f"{x:,}" if isinstance(x, int) else str(x)
def _p(x):
    return "<0.001" if x < 0.001 else f"{x:.3f}" if x < 0.01 else f"{x:.2f}"
def _d(c):  # difference and Newcombe interval in percentage points
    sg = lambda x: f"$-${-x:.1f}" if x < 0 else f"{x:.1f}"
    return f"{100 * c['diff_newcombe95'][0]:.1f}", f"{sg(100 * c['diff_newcombe95'][1])}{' to ' if c['diff_newcombe95'][1] < 0 else '--'}{sg(100 * c['diff_newcombe95'][2])}"
_V = ROOT / "results/r4_rq1.json"
if _V.exists():
    V = json.load(open(_V)); C = V["contrast"]; oc = V["opposite_census"]; rf = V["role_fit_r4"]; fam = V["pinning_share_by_query"]
    u, s = C["untailored_rule"], C["engine_dependent_reclassified_kept_in_n"]
    N.update(RvAwareMis=u["aware"].split("/")[0], RvAwareN=u["aware"].split("/")[1], RvAwareShare=pc(u["aware_share"]),
             RvPinMis=u["pinning"].split("/")[0], RvPinN=u["pinning"].split("/")[1], RvPinShare=pc(u["pinning_share"]),
             RvContrastP=_p(u["fisher_p"]), RvContrastDiff=_d(u)[0], RvContrastCI=_d(u)[1], RvPrintedP=_p(C["printed_rule"]["fisher_p"]),
             RvEngineAware=oc["engine_dependent_no_arg_js"], RvEnginePin=rf["pinning_misfits_engine_dependent"],
             RvSymAwareMis=s["aware"].split("/")[0], RvSymPinMis=s["pinning"].split("/")[0], RvSymAwareShare=pc(s["aware_share"]),
             RvSymPinShare=pc(s["pinning_share"]), RvSymP=_p(s["fisher_p"]), RvSymDiff=_d(s)[0], RvSymCI=_d(s)[1],
             RvNeutralCensus=len(oc["neutral_untailored_rule"]), RvMisfitsAnyRuntime=len(oc["misfits_not_engine_dependent"]),
             RvShareNonAPI=pc(fam["retrieved_by_any_non_api_query"]["share"]), RvShareNonAPIN=fmt(fam["retrieved_by_any_non_api_query"]["n"]),
             RvSharePinQ=pc(fam["only_pinning_api_queries"]["share"]), RvSharePinQN=fmt(fam["only_pinning_api_queries"]["n"]),
             RvShareOppQ=pc(fam["opposite_api_only_among_rest"]["share"]), RvShareOppQN=fmt(fam["opposite_api_only_among_rest"]["n"]),
             RvShareTurkic=pc(fam["family_T"]["share"]), RvShareSOne=pc(fam["family_S1"]["share"]))
_Q = ROOT / "results/r4_rq2_realcode.json"
if _Q.exists():
    Q = json.load(open(_Q)); cg = Q["categories"]
    mis = ("pin_linguistic_misfit", "aware_machine_misfit", "aware_machine_engine_dependent")
    N.update(RvRealLineages=Q["lineages_with_files"], RvRealPinMachN=cg["pin_machine"]["lineages_located_both_sides"],
             RvRealPmdPinMachPre=cg["pin_machine"]["pmd"]["flag_pre"], RvRealProtoPinMachIdeal=cg["pin_machine"]["prototype"]["flag_only_ideal_side"],
             RvRealMisfitN=sum(cg[c]["lineages_located_both_sides"] for c in mis),
             RvRealMisfitPostFlags=sum(cg[c][t]["flag_post"] for c in mis for t in ("prototype", "registry", "pmd", "dotnet") if t in cg[c]),
             RvRealPmdMisfitPre=sum(cg[c]["pmd"]["flag_pre"] for c in mis), RvRealAwareLingN=cg["aware_linguistic"]["lineages_located_both_sides"],
             RvRealRegistryFindings=Q["findings_files"]["registry"])
    if "by_language" in cg["pin_machine"]:  # post hoc, 2026-11-13
        bl = cg["pin_machine"]["by_language"]; lg = lambda c, l: cg[c]["by_language"].get(l, {}).get("n", 0)
        hc = lambda c, lab: cg[c]["human_coded"].get(lab, 0)
        N.update(RvRealPinMachJava=lg("pin_machine", "java"), RvRealPinMachCs=lg("pin_machine", "csharp"),
                 RvRealPinMachJs=lg("pin_machine", "js_ts"), RvRealProtoPinMachPost=cg["pin_machine"]["prototype"]["flag_post"],
                 RvRealMisfitJava=sum(lg(c, l) for c in mis for l in cg[c]["by_language"] if "java" in l.split("+")),
                 RvRealPinMachHumN=cg["pin_machine"]["human_coded_lineages"], RvRealPinMachHumFit=hc("pin_machine", "set1:-/FIT"),
                 RvRealAwareMachN=cg["aware_machine_misfit"]["lineages_located_both_sides"],
                 RvRealAwareMachHumFit=hc("aware_machine_misfit", "set2:LOCALE_AWARE/FIT"),
                 RvRealAwareMachHumOther=hc("aware_machine_misfit", "set2:OTHER/-"),
                 RvRealEngN=cg["aware_machine_engine_dependent"]["lineages_located_both_sides"],
                 RvRealEngHumMisfit=hc("aware_machine_engine_dependent", "set2:LOCALE_AWARE/MISFIT"))
        if "dotnet" in cg["pin_machine"]:
            cs = bl.get("csharp", {}).get("dotnet", {})
            N.update(RvRealDotnetPinMachPre=cs.get("flag_pre", 0), RvRealDotnetPinMachPost=cs.get("flag_post", 0),
                     RvRealDotnetFindings=Q["findings_files"]["dotnet"],
                     RvRealDotnetPinMachPostCAEight=cg["pin_machine"].get("post_rules_lineages", {}).get("dotnet", {}).get("CA1308", 0))
_F = ROOT / "results/r4_reference.json"
if _F.exists():
    F = json.load(open(_F)); e, ci = F["estimates"], F["ci95"]
    W2 = lambda k: f"{100 * ci[k][0]:.1f}--{100 * ci[k][1]:.1f}"
    N.update(RvRefRepos=fmt(F["repositories_with_reference"]), RvRefCommits=fmt(F["reference_commits"]),
             RvRefTest=pc(e["reference_test"]), RvRepairTest=pc(e["repair_test"]), RvRefTestDiff=pc(e["diff_test"]), RvRefTestDiffCI=W2("diff_test"),
             RvRefLoc=pc(e["reference_loctest"]), RvRepairLoc=pc(e["repair_loctest"]), RvRefLocDiff=pc(e["diff_loctest"]), RvRefLocDiffCI=W2("diff_loctest"))
_H = ROOT / "results/r4_human.json"
if _H.exists():
    Hh = json.load(open(_H))
    if "weighted" in Hh:
        w = Hh["weighted"]; lt = Hh["locale_test_regex"]
        N.update(RvHumValMisfit=pc(w["validation_misfit_share"]["estimate"]), RvHumAwareMisfit=pc(w["aware_misfit_share"]["estimate"]),
                 RvHumPinMisfit=pc(w["pinning_misfit_share"]["estimate"]), RvHumLocPrec=pc(lt["precision"]["estimate"]),
                 RvHumLocRecall=pc(lt["recall"]["estimate"]))
        sg = lambda x: f"$-${-x:.1f}" if x < 0 else f"{x:.1f}"
        CI = lambda d: f"{sg(100 * d['ci95'][0])}{' to ' if d['ci95'][0] < 0 else '--'}{sg(100 * d['ci95'][1])}"
        k = Hh["agreement_h1_h2"]; kl = Hh["agreement_h_llm"]
        kk = lambda d: f"{d['kappa']:.2f}"
        other = [k[q]["kappa"] for q in k if not q.endswith("_fit")]
        N.update(RvHumValMisfitCI=CI(w["validation_misfit_share"]), RvHumAwareMisfitCI=CI(w["aware_misfit_share"]),
                 RvHumPinMisfitCI=CI(w["pinning_misfit_share"]),
                 RvHumAwareMisfitEng=pc(w["aware_misfit_share_without_engine_dependent"]["estimate"]),
                 RvHumAwareMisfitEngCI=CI(w["aware_misfit_share_without_engine_dependent"]),
                 RvHumPinMisfitEng=pc(w["pinning_misfit_share_without_engine_dependent"]["estimate"]),
                 RvHumPinMisfitEngCI=CI(w["pinning_misfit_share_without_engine_dependent"]),
                 RvHumDiff=pc(w["aware_minus_pinning"]["estimate"]), RvHumDiffCI=CI(w["aware_minus_pinning"]),
                 RvHumDiffEng=pc(w["aware_minus_pinning_without_engine_dependent"]["estimate"]),
                 RvHumDiffEngCI=CI(w["aware_minus_pinning_without_engine_dependent"]),
                 RvHumNVal=w["coded_n"]["validation_genuine_included"], RvHumNAware=w["coded_n"]["aware"],
                 RvHumNPin=w["coded_n"]["pinning"],
                 RvHumLocPrecCI=CI(lt["precision"]), RvHumLocRecallCI=CI(lt["recall"]),
                 RvHumLocTrue=pc(lt["true_locale_test_share"]["estimate"]), RvHumLocTrueCI=CI(lt["true_locale_test_share"]),
                 RvHumItems=sum(v["items"] for v in Hh["complete"].values()),
                 RvHumKMin=f"{min(other):.2f}", RvHumKMax=f"{max(other):.2f}",
                 RvHumKFitOne=kk(k["set1_fit"]), RvHumKFitTwo=kk(k["set2_fit"]), RvHumKLoc=kk(k["set3_loctest"]),
                 RvHumKRoleLlmMin=f"{min(kl[q]['kappa'] for q in kl if '_role_' in q):.2f}",
                 RvHumKRoleLlmMax=f"{max(kl[q]['kappa'] for q in kl if '_role_' in q):.2f}",
                 RvHumKGenLlmMin=f"{min(kl[q]['kappa'] for q in kl if '_genuine_' in q):.2f}",
                 RvHumKChangeLlmMin=f"{min(kl[q]['kappa'] for q in kl if '_change_' in q):.2f}",
                 RvHumKChangeLlmMax=f"{max(kl[q]['kappa'] for q in kl if '_change_' in q):.2f}")
        if "single_coder" in w:  # post hoc, 2026-11-13
            for tag, c in (("One", "h1"), ("Two", "h2")):
                sc = w["single_coder"][c]
                N.update({f"RvHum{tag}ValMisfit": pc(sc["validation_misfit_share"]), f"RvHum{tag}AwareMisfit": pc(sc["aware_misfit_share"]),
                          f"RvHum{tag}PinMisfit": pc(sc["pinning_misfit_share"]), f"RvHum{tag}Diff": pc(sc["aware_minus_pinning"]),
                          f"RvHum{tag}DiffEng": pc(sc["aware_minus_pinning_without_engine_dependent"])})
json.dump(N, open(ROOT / "results/rq3_numbers.json", "w"), indent=1)
