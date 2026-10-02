"""POST_REVIEW exploratory: can a line-level heuristic infer the text role that the coders assigned?
Cues are fixed below before evaluation; prediction uses only the removed/added lines of the classified edits."""
import csv, json, pathlib, re, collections, sys
ROOT = pathlib.Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "src"))
from analyze_validation import wilson
MACH = re.compile(r"\.(put|get|getOrDefault|containsKey|remove)\(|\bswitch\b|\bcase\s|\.equals(IgnoreCase)?\(\s*\"[\x20-\x7e]*\"\)|[=!]==?\s*['\"][\x20-\x7e]*['\"]|\.(startsWith|endsWith|StartsWith|EndsWith|Contains|contains|includes)\(\s*['\"][\x20-\x7e]*['\"]|\[[^\]]*\.(to(Lower|Upper)(Case|Invariant)?|toLocale(Lower|Upper)Case)\(|(?i:header|key|\bname\(\)|type|\bid\b|path|file|\bext|cmd|command|token|scheme|protocol|mime|\btag|method|field|propert|attr|enum|charset|encoding|host|\burl|\buri|column|table|\bsql|keyword|os\.name|getProperty|\bop\b|format|lang|locale|code|extension|algorithm|option|flag|param|arg|env)")
LING = re.compile(r"(?i:settext|label|title|display|caption|message|search|query|filter|\bui\b|\bview|description|comment|placeholder|tooltip|heading|greeting|user(name)?\b|first_?name|last_?name|full_?name|surname|city|country|address|word|sentence|text\b|translat|i18n|l10n|sort.*name|collat)")
def predict(lines):
    t = " ".join(lines); m, l = bool(MACH.search(t)), bool(LING.search(t))
    return "MACHINE" if m and not l else "LINGUISTIC" if l and not m else "UNKNOWN"
items = []
key = {r["item_id"]: r["sha"] for r in csv.DictReader(open(ROOT / "validation/sample_key.csv"))}
adj = {r["item_id"]: r for r in csv.DictReader(open(ROOT / "validation/adjudicated.csv"))}
ed = collections.defaultdict(list)
for e in csv.DictReader(open(ROOT / "data/processed/repair_edits.csv")): ed[e["sha"]].append(e)
for i, r in adj.items():
    if r["genuine"] == "YES" and r["role"] in ("MACHINE", "LINGUISTIC") and ed.get(key[i]):
        items.append(("main", r["role"], predict([x["removed"] + " " + x["added"] for x in ed[key[i]]])))
G = {}
for f in ("coder_A.csv",):
    pass
A = {r["item_id"]: r for r in csv.DictReader(open(ROOT / "validation/ling/coder_A.csv"))}
B = {r["item_id"]: r for r in csv.DictReader(open(ROOT / "validation/ling/coder_B.csv"))}
D = {r["item_id"]: r for r in csv.DictReader(open(ROOT / "validation/ling/adjudicated_disagreements.csv"))}
L = {json.loads(l)["item_id"]: json.loads(l) for l in open(ROOT / "validation/ling/items.jsonl")}
for i in A:
    role = (D[i] if i in D else A[i])["role"].strip().upper()
    if role in ("MACHINE", "LINGUISTIC"):
        items.append(("towards_aware", role, predict([x["removed"] + " " + x["added"] for x in L[i]["changed_lines"]])))
out = {}
for subset in ("main", "towards_aware", "all"):
    S = [x for x in items if subset == "all" or x[0] == subset]
    cov = [x for x in S if x[2] != "UNKNOWN"]
    res = {"n": len(S), "covered": len(cov), "coverage": round(len(cov) / len(S), 3)}
    for role in ("MACHINE", "LINGUISTIC"):
        tp = sum(1 for x in cov if x[2] == role and x[1] == role); pp = sum(1 for x in cov if x[2] == role); ap = sum(1 for x in S if x[1] == role)
        res[role] = {"precision": f"{tp}/{pp}", "precision_wilson": wilson(tp, pp) if pp else None, "recall": f"{tp}/{ap}"}
    res["accuracy_on_covered"] = round(sum(1 for x in cov if x[1] == x[2]) / len(cov), 3) if cov else None
    out[subset] = res
json.dump(out, open(ROOT / "results/role_heuristic_eval.json", "w"), indent=1); print(json.dumps(out, indent=1))
