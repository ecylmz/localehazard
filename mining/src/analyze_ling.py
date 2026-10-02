"""POST_HOC: role of text in linguistic-direction repairs (two coders + adjudication)."""
import csv, json, pathlib, collections, sys
ROOT = pathlib.Path(__file__).resolve().parents[1]; V = ROOT / "validation/ling"
sys.path.insert(0, str(ROOT / "src")); from analyze_validation import kappa, wilson
L = lambda f: {r["item_id"]: {k: (r[k] or "").strip().upper() for k in ("role", "change")} for r in csv.DictReader(open(f))}
A, B = L(V / "coder_A.csv"), L(V / "coder_B.csv"); ids = sorted(A)
adj = {i: A[i] for i in ids if A[i] == B[i]}
adj.update(L(V / "adjudicated_disagreements.csv"))
assert set(adj) == set(ids)
out = {"n": len(ids), "kappa_role": kappa([A[i]["role"] for i in ids], [B[i]["role"] for i in ids]),
       "raw_role": round(sum(A[i]["role"] == B[i]["role"] for i in ids) / len(ids), 3),
       "kappa_change": kappa([A[i]["change"] for i in ids], [B[i]["change"] for i in ids]),
       "final": {k: dict(collections.Counter(adj[i][k] for i in ids)) for k in ("role", "change")},
       "role_by_change": {c: dict(collections.Counter(adj[i]["role"] for i in ids if adj[i]["change"] == c)) for c in ("LOCALE_AWARE", "UNICODE_FOLD", "OTHER")}}
la = [i for i in ids if adj[i]["change"] == "LOCALE_AWARE"]
m = [i for i in la if adj[i]["role"] in ("MACHINE", "MIXED")]
out["locale_aware_machine_or_mixed"] = {"k": len(m), "n": len(la), "share": round(len(m) / len(la), 4), "wilson95": wilson(len(m), len(la))}
json.dump(out, open(ROOT / "results/rq3_ling_roles.json", "w"), indent=1); print(json.dumps(out, indent=1))
