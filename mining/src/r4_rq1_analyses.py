"""Round-4 RQ1 analyses (post hoc, after the internal pre-submission review of 2026-11-08; protocol/DEVIATIONS.md, 2026-11-09).

All inputs are existing deposited files; no new data.
(a) role fit with the corrected role-neutral rule: case folding, or a fixed locale without case tailoring
    (any locale other than tr, az, lt);
(b) directional contrast: role-inconsistent share among locale-aware moves (census of the frozen classifier's
    opposite-direction lineages) vs. pinning changes (random validation sample), with a two-sided Fisher exact
    test and a Newcombe hybrid-score interval, and again with engine-dependent no-argument JavaScript
    toLocaleLowerCase()/toLocaleUpperCase() calls classified alike in both arms;
(c) pinning-only share per query family.
"""
import csv, json, math, pathlib, re, collections, sys

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
dirs = lambda sha: sorted({e["direction"] for e in edits[sha]})
out = {}


def log_choose(n, k):
    return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)


def fisher_two_sided(a, b, c, d):
    """Two-sided Fisher exact test for [[a, b], [c, d]]: sum of tables no more probable than the observed one."""
    r1, c1, n = a + b, a + c, a + b + c + d
    lo, hi = max(0, c1 - (n - r1)), min(r1, c1)
    lp = lambda x: log_choose(c1, x) + log_choose(n - c1, r1 - x) - log_choose(n, r1)
    p0 = lp(a)
    return min(1.0, sum(math.exp(lp(x)) for x in range(lo, hi + 1) if lp(x) <= p0 + 1e-7))


def newcombe(k1, n1, k2, n2):
    """Newcombe (1998) hybrid-score interval for p1 - p2 from Wilson intervals."""
    p1, p2 = k1 / n1, k2 / n2
    (l1, u1), (l2, u2) = wilson(k1, n1), wilson(k2, n2)
    d = p1 - p2
    return [round(d, 4), round(d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2), 4), round(d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2), 4)]


def contrast(k1, n1, k2, n2):
    return {"aware": f"{k1}/{n1}", "pinning": f"{k2}/{n2}", "aware_share": round(k1 / n1, 4), "pinning_share": round(k2 / n2, 4),
            "fisher_p": round(fisher_two_sided(k1, n1 - k1, k2, n2 - k2), 4), "diff_newcombe95": newcombe(k1, n1, k2, n2)}


# r3_audit_analyses.py used a bare "fold" alternative, which also matches identifiers such as folderPath (L069).
FOLD = re.compile(r"\.casefold\(|ToLowerInvariant\b|\bfoldCase\(|toFoldCase\(")
TAILORED = r"(?:tr|az|lt)"
FIXED_UNTAILORED = re.compile(
    r"toLocale(?:Lower|Upper)Case\(\s*\[?\s*['\"](?!" + TAILORED + r"\b)[A-Za-z]{2}"
    r"|Locale\.(?:ENGLISH|US|UK|ROOT|FRENCH|FRANCE|GERMAN|GERMANY|ITALIAN|ITALY|CANADA|CHINESE|JAPANESE|KOREAN)\b"
    r"|new Locale\(\s*\"(?!" + TAILORED + r"\b)[a-z]{2}\""
    r"|CultureInfo(?:\.GetCultureInfo)?\(\s*\"(?!" + TAILORED + r"\b)[a-z]{2}"
    r"|forLanguageTag\(\s*\"(?!" + TAILORED + r"\b)[a-z]{2}", re.I)
JS_NOARG = re.compile(r"toLocale(?:Lower|Upper)Case\(\s*\)")


def neutral_added(text):
    return bool(FOLD.search(text) or FIXED_UNTAILORED.search(text))


# ---------- (a) role fit in the validation sample ----------
key = {r["item_id"]: r for r in csv.DictReader(open(ROOT / "validation/sample_key.csv"))}
adj = {r["item_id"]: r for r in csv.DictReader(open(ROOT / "validation/adjudicated.csv"))}
g = [i for i in key if key[i]["sample"] == "included" and key[i]["sha"] in included and adj[i]["genuine"] == "YES"]


def engine_dependent_pinning(sha):
    """Every pinning edit removes a no-argument JavaScript toLocale*Case() call."""
    pe = [e for e in edits[sha] if e["direction"] == "MACHINE_PINNING"]
    return bool(pe) and all(e["ecosystem"] == "js" and JS_NOARG.search(e["removed"]) for e in pe)


def engine_dependent_aware(sha):
    ae = [e for e in edits[sha] if e["direction"] == "LINGUISTIC_REPAIR"]
    return bool(ae) and all(e["ecosystem"] == "js" and JS_NOARG.search(e["added"]) for e in ae)


cat = collections.Counter(); items = collections.defaultdict(list)
pin_n = pin_mis = pin_mis_engine = 0; pin_engine_ids = []
for i in g:
    sha = key[i]["sha"]; ds = dirs(sha); role = adj[i]["role"]
    opp = [e for e in edits[sha] if e["direction"] == "LINGUISTIC_REPAIR"]
    if ds == ["LINGUISTIC_REPAIR"] and all(neutral_added(e["added"]) for e in opp):
        k = "role_neutral"
    elif ds == ["MACHINE_PINNING"]:
        k = {"MACHINE": "fit", "LINGUISTIC": "pin_on_linguistic", "MIXED": "mixed"}.get(role, "unclear")
        pin_n += 1
        if role == "LINGUISTIC":
            pin_mis += 1
            if engine_dependent_pinning(sha):
                pin_mis_engine += 1; pin_engine_ids.append(i)
    elif ds == ["LINGUISTIC_REPAIR"]:
        k = {"LINGUISTIC": "fit", "MACHINE": "aware_on_machine", "MIXED": "mixed"}.get(role, "unclear")
        if k == "aware_on_machine" and engine_dependent_aware(sha):
            items["aware_on_machine_engine_dependent"].append(i)
    else:
        k = "unclear"
    cat[k] += 1; items[k].append(i)
mis = cat["pin_on_linguistic"] + cat["aware_on_machine"]
pin_engine_all = [i for i in g if dirs(key[i]["sha"]) == ["MACHINE_PINNING"] and engine_dependent_pinning(key[i]["sha"])]
out["role_fit_r4"] = {"n": len(g), **dict(cat), "misfit_combinations": mis, "misfit_wilson": wilson(mis, len(g)),
                      "pinning_n": pin_n, "pinning_misfits": pin_mis, "pinning_misfits_engine_dependent": pin_mis_engine,
                      "pinning_engine_dependent_all": len(pin_engine_all),
                      "items": {k: sorted(v) for k, v in items.items() if k != "fit"},
                      "pinning_engine_misfit_items": sorted(pin_engine_ids)}

# ---------- (b) opposite-direction census and the directional contrast ----------
L = ROOT / "validation/ling"
rd = lambda f: {r["item_id"]: {k: (r[k] or "").strip().upper() for k in ("role", "change")} for r in csv.DictReader(open(L / f))}
A, B = rd("coder_A.csv"), rd("coder_B.csv")
fin = {i: A[i] for i in A if A[i] == B[i]}
fin.update(rd("adjudicated_disagreements.csv"))
litems = {json.loads(l)["item_id"]: json.loads(l) for l in open(L / "items.jsonl")}
aware = [i for i in fin if fin[i]["change"] == "LOCALE_AWARE"]
added = lambda i: " ".join(x["added"] for x in litems[i]["changed_lines"])
mach = [i for i in aware if fin[i]["role"] == "MACHINE"]
neutral_old = [i for i in mach if re.search(r"toLocale(Lower|Upper)Case\(\s*\[?\s*['\"]en|Locale\.(ENGLISH|US)\b", added(i), re.I)]
neutral_new = [i for i in mach if neutral_added(added(i))]
engine = [i for i in mach if i not in neutral_new and JS_NOARG.search(added(i))]
mis_new = [i for i in mach if i not in neutral_new]
out["opposite_census"] = {"n_aware": len(aware), "machine": len(mach), "neutral_english_rule": sorted(neutral_old),
                          "neutral_untailored_rule": sorted(neutral_new), "misfits_printed_rule": len(mach) - len(neutral_old),
                          "misfits_untailored_rule": len(mis_new), "engine_dependent_no_arg_js": len(engine),
                          "engine_dependent_items": sorted(engine),
                          "misfits_not_engine_dependent": sorted(set(mis_new) - set(engine))}

out["contrast"] = {
    "printed_rule": contrast(len(mach) - len(neutral_old), len(aware), pin_mis, pin_n),
    "untailored_rule": contrast(len(mis_new), len(aware), pin_mis, pin_n),
    "engine_dependent_reclassified_kept_in_n": contrast(len(mis_new) - len(engine), len(aware), pin_mis - pin_mis_engine, pin_n),
    "engine_dependent_dropped_from_n": contrast(len(mis_new) - len(engine), len(aware) - len(engine),
                                                pin_mis - pin_mis_engine, pin_n - len(pin_engine_all)),
}

# ---------- (c) pinning-only share per query family ----------
qset = lambda c: set(c["queries"].split(";"))
pin = lambda c: dirs(c["sha"]) == ["MACHINE_PINNING"]
FAM = {"pinning_api": {"J1", "J2", "J3", "J4", "J5", "N1", "N2", "N3", "N4", "C1", "C2", "C3", "S2"},
       "non_api": {"T1", "T2", "T3", "T4", "T5", "G1", "G2", "G3", "A1", "A2", "A3", "A4", "A5", "D1", "D2"}}
fam = {"all": boot_share(reps, pin, repo),
       "manuscript_subset_not_only_pinning_queries": boot_share([c for c in reps if not qset(c) <= FAM["pinning_api"]], pin, repo),
       "retrieved_by_any_non_api_query": boot_share([c for c in reps if qset(c) & FAM["non_api"]], pin, repo),
       "only_pinning_api_queries": boot_share([c for c in reps if qset(c) <= FAM["pinning_api"]], pin, repo),
       "opposite_api_only_among_rest": boot_share([c for c in reps if not qset(c) <= FAM["pinning_api"] and not qset(c) & FAM["non_api"]], pin, repo)}
for name, ids in [("T", "T1 T2 T3 T4 T5"), ("G", "G1 G2 G3"), ("A", "A1 A2 A3 A4 A5"), ("D", "D1 D2"), ("J", "J1 J2 J3 J4 J5"),
                  ("N", "N1 N2 N3 N4"), ("C", "C1 C2 C3"), ("S1", "S1"), ("S2", "S2"), ("S3", "S3")]:
    sub = [c for c in reps if qset(c) & set(ids.split())]
    fam["family_" + name] = boot_share(sub, pin, repo) if sub else None
out["pinning_share_by_query"] = fam

json.dump(out, open(ROOT / "results/r4_rq1.json", "w"), indent=1, ensure_ascii=False)
print(json.dumps(out, indent=1, ensure_ascii=False))
