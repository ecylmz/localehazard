"""Agreement analysis for the two human coders (exports of human_coding.html).

Usage: python3 analyze_human.py coder1.csv coder2.csv
Writes agreement.json (human-human and human-LLM agreement before reconciliation) and
disagreements.csv (items the two humans must reconcile; no LLM label is included).
"""
import csv, json, pathlib, sys, collections

HERE = pathlib.Path(__file__).resolve().parent
V = HERE.parent
QS = {"1": ["genuine", "role", "trigger", "family", "fit"], "2": ["change", "role", "fit"]}
GATE = {"1": ("genuine", lambda v: v == "YES"), "2": ("change", lambda v: v in ("LOCALE_AWARE", "UNICODE_FOLD"))}


def read(p):
    rows = {r["item_id"]: r for r in csv.DictReader(open(p, encoding="utf-8-sig"))}
    return rows, next(iter(rows.values()))["coder"]


def kappa(pairs):
    n = len(pairs)
    if not n:
        return None, None
    po = sum(a == b for a, b in pairs) / n
    ca, cb = collections.Counter(a for a, _ in pairs), collections.Counter(b for _, b in pairs)
    pe = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / n / n
    return round(po, 3), (round((po - pe) / (1 - pe), 3) if pe < 1 else None)


def compare(a, b, ids, s):
    out = {}
    gk, gate = GATE[s]
    for q in QS[s]:
        pairs = [(a[i][q], b[i][q]) for i in ids if a[i][q] and b[i][q] and (q == gk or (gate(a[i][gk]) and gate(b[i][gk])))]
        raw, k = kappa(pairs)
        out[q] = {"n": len(pairs), "raw_agreement": raw, "kappa": k}
    return out


def llm_labels():
    key = {r["human_id"]: r for r in csv.DictReader(open(HERE / "key.csv"))}
    adj = {r["item_id"]: r for r in csv.DictReader(open(V / "adjudicated.csv"))}
    la = {r["item_id"]: r for r in csv.DictReader(open(V / "ling/coder_A.csv"))}
    lb = {r["item_id"]: r for r in csv.DictReader(open(V / "ling/coder_B.csv"))}
    ld = {r["item_id"]: r for r in csv.DictReader(open(V / "ling/adjudicated_disagreements.csv"))}
    out = {}
    for h, k in key.items():
        o = k["orig_id"]
        if k["set"] == "1":
            out[h] = {q: adj[o][q] for q in ("genuine", "role", "trigger", "family")}
        else:
            src = ld[o] if o in ld else la[o]
            if o not in ld:
                assert (la[o]["role"], la[o]["change"]) == (lb[o]["role"], lb[o]["change"]), o
            out[h] = {"change": src["change"], "role": src["role"]}
    return out


def main(p1, p2):
    a, ca = read(p1)
    b, cb = read(p2)
    llm = llm_labels()
    res = {"coders": [ca, cb], "complete": {ca: sum(r["complete"] == "1" for r in a.values()), cb: sum(r["complete"] == "1" for r in b.values())}}
    dis = []
    for s in ("1", "2"):
        ids = [i for i in a if a[i]["set"] == s and a[i]["complete"] == "1" and b[i]["complete"] == "1"]
        res[f"set{s}"] = {"both_complete": len(ids), "human_human": compare(a, b, ids, s)}
        for name, h in ((ca, a), (cb, b)):
            hl = {i: {q: llm[i].get(q, "") for q in QS[s]} for i in ids}
            res[f"set{s}"][f"{name}_vs_llm"] = {q: v for q, v in compare(h, hl, ids, s).items() if q != "fit"}
        for i in ids:
            diff = [q for q in QS[s] if a[i][q] != b[i][q]]
            if diff:
                dis.append({"item_id": i, "set": s, "questions": ";".join(diff),
                            **{f"{q}_{ca}": a[i][q] for q in QS[s]}, **{f"{q}_{cb}": b[i][q] for q in QS[s]},
                            f"note_{ca}": a[i]["note"], f"note_{cb}": b[i]["note"], "reconciled": ""})
    json.dump(res, open(HERE / "agreement.json", "w"), indent=1, ensure_ascii=False)
    if dis:
        cols = sorted({k for d in dis for k in d}, key=lambda k: (k not in ("item_id", "set", "questions"), k == "reconciled", k))
        with open(HERE / "disagreements.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=cols); w.writeheader(); w.writerows(dis)
    print(json.dumps(res, indent=1, ensure_ascii=False))
    print(len(dis), "items to reconcile -> disagreements.csv")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
