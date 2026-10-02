"""RQ3 validation: inter-coder agreement (pre-adjudication) and classifier precision (adjudicated)."""
import csv, json, math, pathlib, collections

ROOT = pathlib.Path(__file__).resolve().parents[1]
V = ROOT / "validation"
Q = ["genuine", "role", "trigger", "family"]


def load(fn):
    rows = {}
    for r in csv.DictReader(open(fn)):
        rows[r["item_id"].strip()] = {q: (r.get(q) or "").strip().upper() for q in Q}
    return rows


def kappa(a, b):
    n = len(a)
    if n == 0:
        return None
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = collections.Counter(a), collections.Counter(b)
    pe = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / n / n
    return round((po - pe) / (1 - pe), 3) if pe < 1 else 1.0


def wilson(k, n, z=1.96):
    if n == 0:
        return [None, None]
    p = k / n; d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(c - h, 4), round(c + h, 4)]


def main():
    key = {r["item_id"]: r["sample"] for r in csv.DictReader(open(V / "sample_key.csv"))}
    A, B = load(V / "coder_A.csv"), load(V / "coder_B.csv")
    adj = load(V / "adjudicated.csv")
    ids = sorted(key)
    missing = [i for i in ids if i not in A or i not in B or i not in adj]
    assert not missing, missing[:5]
    out = {"items": len(ids), "agreement": {}}
    for q in Q:
        if q == "genuine":
            sel = ids
        else:
            sel = [i for i in ids if A[i]["genuine"] == "YES" and B[i]["genuine"] == "YES"]
        a = [A[i][q] for i in sel]; b = [B[i][q] for i in sel]
        out["agreement"][q] = {"n": len(sel), "raw": round(sum(x == y for x, y in zip(a, b)) / len(sel), 3) if sel else None,
                               "kappa": kappa(a, b)}
    inc = [i for i in ids if key[i] == "included"]; exc = [i for i in ids if key[i] == "excluded"]
    gen = [i for i in inc if adj[i]["genuine"] == "YES"]
    out["precision"] = {"k": len(gen), "n": len(inc), "share": round(len(gen) / len(inc), 4), "wilson95": wilson(len(gen), len(inc))}
    out["included_unclear"] = sum(1 for i in inc if adj[i]["genuine"] == "UNCLEAR")
    missed = [i for i in exc if adj[i]["genuine"] == "YES"]
    out["excluded_genuine"] = {"k": len(missed), "n": len(exc), "share": round(len(missed) / len(exc), 4) if exc else None,
                               "wilson95": wilson(len(missed), len(exc))}
    out["role_genuine_included"] = dict(collections.Counter(adj[i]["role"] for i in gen))
    out["trigger_genuine_included"] = dict(collections.Counter(adj[i]["trigger"] for i in gen))
    out["family_genuine_included"] = dict(collections.Counter(adj[i]["family"] for i in gen))
    out["role_genuine_excluded"] = dict(collections.Counter(adj[i]["role"] for i in missed))
    out["family_genuine_excluded"] = dict(collections.Counter(adj[i]["family"] for i in missed))
    json.dump(out, open(ROOT / "results/rq3_validation.json", "w"), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
