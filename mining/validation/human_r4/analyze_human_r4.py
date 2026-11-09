"""Analyse the round-4 human coding (validation/human_r4/).

Usage: python3 validation/human_r4/analyze_human_r4.py H1.csv H2.csv [reconciled.csv]
  H1.csv, H2.csv   exports of the two human coders (independent labels)
  reconciled.csv   optional: the labels after the two coders reconciled their disagreements (same columns)
Writes results/r4_human.json and validation/human_r4/disagreements_r4.csv.

(1) Agreement before reconciliation: raw agreement and Cohen's kappa per question, human-human and human-LLM.
(2) With reconciled labels: stratum-weighted estimates (strata in key_r4.csv) of
    - the share of genuine validation-sample changes whose new behaviour misfits the use of the text (Q5 = MISFIT),
    - the directional contrast with Q5: MISFIT share among LOCALE_AWARE opposite-direction changes vs. among
      pinning changes in the validation sample, also without engine-dependent no-argument JavaScript calls,
    - precision and recall of the locale-test regular expression (Set 3, Q6), weighted by stratum size.
    Intervals: percentile bootstrap within strata (2,000 replicates, seed 20261109).
"""
import csv, json, math, pathlib, random, re, sys, collections

ROOT = pathlib.Path(__file__).resolve().parents[2]
V = ROOT / "validation"; H = pathlib.Path(__file__).resolve().parent
rng = random.Random(20261109); B = 2000
key = {r["human_id"]: r for r in csv.DictReader(open(H / "key_r4.csv"))}
read = lambda p: {r["item_id"]: r for r in csv.DictReader(open(p, encoding="utf-8-sig"))}
h1, h2 = read(sys.argv[1]), read(sys.argv[2])
rec = read(sys.argv[3]) if len(sys.argv) > 3 else None


def kappa(pairs):
    pairs = [(a, b) for a, b in pairs if a and b]
    if not pairs:
        return {"n": 0}
    n = len(pairs); po = sum(a == b for a, b in pairs) / n
    ca, cb = collections.Counter(a for a, _ in pairs), collections.Counter(b for _, b in pairs)
    pe = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / (n * n)
    return {"n": n, "raw": round(po, 4), "kappa": round((po - pe) / (1 - pe), 4) if pe < 1 else None}


# ---------- LLM labels for comparison ----------
adj = {r["item_id"]: r for r in csv.DictReader(open(V / "adjudicated.csv"))}
L = V / "ling"
rd = lambda f: {r["item_id"]: {k: (r[k] or "").strip().upper() for k in ("role", "change")} for r in csv.DictReader(open(L / f))}
A, Bc = rd("coder_A.csv"), rd("coder_B.csv")
fin = {i: A[i] for i in A if A[i] == Bc[i]}; fin.update(rd("adjudicated_disagreements.csv"))
llm = {}
for hid, k in key.items():
    if k["set"] == "1":
        a = adj[k["orig_id"]]; llm[hid] = {"genuine": a["genuine"], "role": a["role"], "trigger": a["trigger"], "family": a["family"]}
    elif k["set"] == "2":
        llm[hid] = {"change": fin[k["orig_id"]]["change"], "role": fin[k["orig_id"]]["role"]}

QS = {"1": ["genuine", "role", "trigger", "family", "fit"], "2": ["change", "role", "fit"], "3": ["loctest"]}
out = {"agreement_h1_h2": {}, "agreement_h_llm": {}, "complete": {}}
for s, qs in QS.items():
    ids = [h for h in key if key[h]["set"] == s]
    out["complete"][s] = {"items": len(ids), "h1": sum(h1.get(i, {}).get("complete") == "1" for i in ids),
                          "h2": sum(h2.get(i, {}).get("complete") == "1" for i in ids)}
    for q in qs:
        out["agreement_h1_h2"][f"set{s}_{q}"] = kappa([(h1.get(i, {}).get(q, ""), h2.get(i, {}).get(q, "")) for i in ids])
        if s != "3" and q != "fit":
            for nm, hc in (("h1", h1), ("h2", h2)):
                out["agreement_h_llm"][f"set{s}_{q}_{nm}"] = kappa([(hc.get(i, {}).get(q, ""), llm[i].get(q, "")) for i in ids])
with open(H / "disagreements_r4.csv", "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["item_id", "set", "question", "h1", "h2", "h1_note", "h2_note"])
    for hid in sorted(key):
        for q in QS[key[hid]["set"]]:
            a, b = h1.get(hid, {}).get(q, ""), h2.get(hid, {}).get(q, "")
            if a != b:
                w.writerow([hid, key[hid]["set"], q, a, b, h1.get(hid, {}).get("note", ""), h2.get(hid, {}).get("note", "")])

# ---------- stratum-weighted estimates from reconciled labels ----------
if rec:
    P = ROOT / "data/processed"
    edits = collections.defaultdict(list)
    for e in csv.DictReader(open(P / "repair_edits.csv")):
        edits[e["sha"]].append(e)
    JS_NOARG = re.compile(r"toLocale(?:Lower|Upper)Case\(\s*\)")
    pin_only = lambda sha: bool(edits[sha]) and all(e["direction"] == "MACHINE_PINNING" for e in edits[sha])
    eng_pin = lambda sha: pin_only(sha) and all(e["ecosystem"] == "js" and JS_NOARG.search(e["removed"]) for e in edits[sha])
    eng_aware = lambda sha: bool(edits[sha]) and all(e["ecosystem"] == "js" and JS_NOARG.search(e["added"]) for e in edits[sha] if e["direction"] == "LINGUISTIC_REPAIR")
    # weights: census strata weight 1; REST items weighted by (pool size in their set) / (drawn in their set)
    pool = {"1": 210 - 15, "2": 181 - 40}
    drawn = collections.Counter(k["set"] for k in key.values() if k["stratum"] == "REST")
    wt = lambda h: 1.0 if key[h]["stratum"] != "REST" else pool[key[h]["set"]] / drawn[key[h]["set"]]

    def boot(groups, stat):
        """groups: {stratum: [items]}; resample within strata."""
        est = stat({g: v for g, v in groups.items()})
        reps = sorted(stat({g: [rng.choice(v) for _ in v] if v else [] for g, v in groups.items()}) for _ in range(B))
        return {"estimate": None if est is None else round(est, 4),
                "ci95": [round(reps[int(0.025 * B)], 4), round(reps[int(0.975 * B) - 1], 4)] if est is not None else None}

    def wshare(groups, num, den):
        n = sum(wt(h) for v in groups.values() for h in v if den(h)); k = sum(wt(h) for v in groups.values() for h in v if den(h) and num(h))
        return k / n if n else None

    lab = lambda h, q: rec.get(h, {}).get(q, "")
    s1 = {st: [h for h in key if key[h]["set"] == "1" and key[h]["stratum"] == st] for st in ("S1_PIN_LING", "REST")}
    s2 = {st: [h for h in key if key[h]["set"] == "2" and key[h]["stratum"] == st] for st in ("S2_AWARE_MACHINE", "REST")}
    inc = {r["sha"] for r in csv.DictReader(open(P / "commits_lineages.csv"))}
    k1 = {r["item_id"]: r for r in csv.DictReader(open(V / "sample_key.csv"))}
    genuine_inc = lambda h: lab(h, "genuine") == "YES" and k1[key[h]["orig_id"]]["sample"] == "included" and key[h]["sha"] in inc
    out["weighted"] = {
        "validation_misfit_share": boot(s1, lambda g: wshare(g, lambda h: lab(h, "fit") == "MISFIT", genuine_inc)),
        "aware_misfit_share": boot(s2, lambda g: wshare(g, lambda h: lab(h, "fit") == "MISFIT", lambda h: lab(h, "change") == "LOCALE_AWARE")),
        "pinning_misfit_share": boot(s1, lambda g: wshare(g, lambda h: lab(h, "fit") == "MISFIT", lambda h: genuine_inc(h) and pin_only(key[h]["sha"]))),
        "aware_misfit_share_without_engine_dependent": boot(s2, lambda g: wshare(g, lambda h: lab(h, "fit") == "MISFIT" and not eng_aware(key[h]["sha"]), lambda h: lab(h, "change") == "LOCALE_AWARE")),
        "pinning_misfit_share_without_engine_dependent": boot(s1, lambda g: wshare(g, lambda h: lab(h, "fit") == "MISFIT" and not eng_pin(key[h]["sha"]), lambda h: genuine_inc(h) and pin_only(key[h]["sha"]))),
        "weights": {"pool": pool, "drawn_rest": dict(drawn)},
    }
    s3 = collections.defaultdict(list)
    for h in key:
        if key[h]["set"] == "3":
            s3[key[h]["stratum"]].append(h)
    size = {st: int(key[v[0]]["stratum_size"]) for st, v in s3.items()}
    yes = lambda h: lab(h, "loctest") == "YES"
    def p(g, st):
        v = [h for h in g[st] if lab(h, "loctest") in ("YES", "NO")]
        return sum(yes(h) for h in v) / len(v) if v else 0.0
    prec = lambda g: p(g, "positive")
    def recall(g):
        tp = size["positive"] * p(g, "positive")
        fn = size["negative_test_change"] * p(g, "negative_test_change") + size["negative_no_test_change"] * p(g, "negative_no_test_change")
        return tp / (tp + fn) if tp + fn else None
    out["locale_test_regex"] = {"precision": boot(s3, prec), "recall": boot(s3, recall),
                                "true_locale_test_share": boot(s3, lambda g: sum(size[st] * p(g, st) for st in size) / sum(size.values())),
                                "unclear": sum(lab(h, "loctest") == "UNCLEAR" for v in s3.values() for h in v), "strata": size}

out_path = ROOT / "results/r4_human.json"
json.dump(out, open(out_path, "w"), indent=1)
print(json.dumps(out, indent=1))
