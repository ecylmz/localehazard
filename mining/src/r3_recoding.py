"""Independent LLM re-coding of the RQ1 samples (post hoc, 2026-10-30/31).

Both samples were re-coded on the blinded page validation/human/for_coders/ (new IDs, seeded order, no model label):
D1 = OpenAI Codex CLI, gpt-6.1-sol, reasoning high (cross-family); D2 = Anthropic Claude Opus 5.5, reasoning high
(same family as the original coders). Neither is a human coder (validation/human/responses/PROVENANCE.md).
For each label source we report agreement with the adjudicated original labels and recompute the headline figures.
Writes results/r3_recoding.json.
"""
import csv, json, pathlib, re, collections, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from analyze_validation import kappa, wilson
from analyze_mining import VENDORED

V = ROOT / "validation"; H = V / "human"
up = lambda r, ks: {k: (r.get(k) or "").strip().upper() for k in ks}
Q1, Q2 = ("genuine", "role", "trigger", "family"), ("change", "role")

# original (adjudicated) labels, keyed by original item id
orig1 = {r["item_id"]: up(r, Q1) for r in csv.DictReader(open(V / "adjudicated.csv"))}
la, lb = ({r["item_id"]: up(r, Q2) for r in csv.DictReader(open(V / f"ling/coder_{c}.csv"))} for c in "AB")
orig2 = {i: la[i] for i in la if la[i] == lb[i]}
orig2.update({r["item_id"]: up(r, Q2) for r in csv.DictReader(open(V / "ling/adjudicated_disagreements.csv"))})

# re-coder labels, mapped back to original ids through the blinding key
key = {r["human_id"]: r for r in csv.DictReader(open(H / "key.csv"))}
def recoder(fn):
    s1, s2 = {}, {}
    for r in csv.DictReader(open(H / "responses" / fn, encoding="utf-8-sig")):
        k = key[r["item_id"]]
        (s1 if k["set"] == "1" else s2)[k["orig_id"]] = up(r, Q1 + ("change", "fit"))
    return s1, s2
SRC = {"original": (orig1, orig2), "D1_codex": recoder("human_coding_D1_2026-10-30.csv"), "D2_claude": recoder("human_coding_D2_2026-10-30.csv")}

sample = {r["item_id"]: r for r in csv.DictReader(open(V / "sample_key.csv"))}
included = {r["sha"] for r in csv.DictReader(open(ROOT / "data/processed/commits_lineages.csv"))}
edits = collections.defaultdict(list)
for e in csv.DictReader(open(ROOT / "data/processed/repair_edits.csv")):
    if not VENDORED.search(e["file"]):
        edits[e["sha"]].append(e)
items2 = {json.loads(l)["item_id"]: json.loads(l) for l in open(V / "ling/items.jsonl")}
RC = json.load(open(ROOT / "results/rq3_post_review.json"))["recall_turkic_subframe"]  # sub-frame inclusion counts

# same rules as r3_audit_analyses.py (role fit) and post_review_rq3.py (target locale)
FOLD = re.compile(r"\.casefold\(|ToLowerInvariant|fold", re.I)
ENGLISH = re.compile(r"toLocale(Lower|Upper)Case\(\s*\[?\s*['\"]en|Locale\.(ENGLISH|US|UK)\b|CultureInfo\(\s*\"en", re.I)
def neutral(sha):
    opp = [e for e in edits[sha] if e["direction"] == "LINGUISTIC_REPAIR"]
    return bool(opp) and all(FOLD.search(e["added"]) or ENGLISH.search(e["added"]) for e in opp)
def english_target(it):
    add = " ".join(x["added"] for x in it["changed_lines"])
    return bool(re.search(r"toLocale(Lower|Upper)Case\(\s*\[?\s*['\"]en", add) or re.search(r"Locale\.(ENGLISH|US)\b", add))

def figures(s1, s2):
    inc = [i for i in sample if sample[i]["sample"] == "included"]; exc = [i for i in sample if sample[i]["sample"] == "excluded"]
    gen = [i for i in inc if s1[i]["genuine"] == "YES"]
    v2 = [i for i in inc if sample[i]["sha"] in included]; g2 = [i for i in v2 if s1[i]["genuine"] == "YES"]
    cat = collections.Counter()
    for i in g2:
        sha = sample[i]["sha"]; ds = sorted({e["direction"] for e in edits[sha]}); role = s1[i]["role"]
        if ds == ["LINGUISTIC_REPAIR"] and neutral(sha): k = "role_neutral"
        elif ds == ["MACHINE_PINNING"]: k = {"MACHINE": "fit", "LINGUISTIC": "pin_on_linguistic", "MIXED": "mixed"}.get(role, "unclear")
        elif ds == ["LINGUISTIC_REPAIR"]: k = {"LINGUISTIC": "fit", "MACHINE": "aware_on_machine", "MIXED": "mixed"}.get(role, "unclear")
        else: k = "unclear"
        cat[k] += 1
    mis = cat["pin_on_linguistic"] + cat["aware_on_machine"]
    neg = sum(1 for i in exc if s1[i]["genuine"] == "YES")
    rec = lambda p, n: RC["included"] * p / (RC["included"] * p + RC["excluded_nonformat"] * n)
    aware = [i for i in s2 if s2[i]["change"] == "LOCALE_AWARE"]
    mach = [i for i in aware if s2[i]["role"] == "MACHINE"]
    cdm = [i for i in mach if not english_target(items2[i])]
    return {"precision_frozen": {"k": len(gen), "n": len(inc), "wilson95": wilson(len(gen), len(inc))},
            "precision_v2": {"k": len(g2), "n": len(v2), "wilson95": wilson(len(g2), len(v2))},
            "excluded_genuine": {"k": neg, "n": len(exc)}, "recall_turkic_subframe": round(rec(len(g2) / len(v2), neg / len(exc)), 3),
            "role_fit": {"n": len(g2), **dict(cat), "misfit": mis, "misfit_wilson": wilson(mis, len(g2))},
            "trigger_genuine_included": dict(collections.Counter(s1[i]["trigger"] for i in gen)),
            "trigger_v2": dict(collections.Counter(s1[i]["trigger"] for i in g2)),
            "opposite": {"n": len(s2), "locale_aware": len(aware), "fold": sum(1 for i in s2 if s2[i]["change"] == "UNICODE_FOLD"),
                         "machine": len(mach), "role_inconsistent": len(cdm), "role_inconsistent_wilson": wilson(len(cdm), len(aware))}}

def agree(x, y):
    (a1, a2), (b1, b2) = SRC[x], SRC[y]
    out = {}
    ids = sorted(a1)
    for q in Q1:
        sel = ids if q == "genuine" else [i for i in ids if a1[i]["genuine"] == "YES" and b1[i]["genuine"] == "YES"]
        p = [(a1[i][q], b1[i][q]) for i in sel]
        out["set1_" + q] = {"n": len(p), "raw": round(sum(u == v for u, v in p) / len(p), 3), "kappa": kappa(*zip(*p))}
    ids = sorted(a2)
    for q in Q2:
        sel = ids if q == "change" else [i for i in ids if a2[i]["change"] != "OTHER" and b2[i]["change"] != "OTHER"]
        p = [(a2[i][q], b2[i][q]) for i in sel]
        out["set2_" + q] = {"n": len(p), "raw": round(sum(u == v for u, v in p) / len(p), 3), "kappa": kappa(*zip(*p))}
    return out

out = {"figures": {s: figures(*SRC[s]) for s in SRC},
       "agreement": {f"{x}_vs_{y}": agree(x, y) for x, y in (("D1_codex", "original"), ("D2_claude", "original"), ("D1_codex", "D2_claude"))}}
json.dump(out, open(ROOT / "results/r3_recoding.json", "w"), indent=1)
print(json.dumps(out, indent=1))
