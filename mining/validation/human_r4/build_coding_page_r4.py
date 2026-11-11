"""Build the round-4 blinded human-coding page (validation/human_r4/).

Design: protocol/DEVIATIONS.md, 2026-11-09 (stratified subset; Set 3 locale-test validation). Per coder:
  Stratum S2_AWARE_MACHINE: all opposite-direction lineages that the LLM labels code LOCALE_AWARE on MACHINE or
                            MIXED text (40).
  Stratum S1_PIN_LING:      all validation items that pin linguistic or mixed text by the LLM labels (15).
  Stratum REST:             105 items drawn at random from the remaining items of Sets 1 and 2 (seed 20261109).
  Set 3:                    the 100 locale-test lineages of set3_items.jsonl (no indicator value shown).
Items get new IDs (A/B/C + number) in a seeded order. No model label, note or aggregate is embedded. The key with
strata and stratum sizes goes to key_r4.csv (keep it away from coders). The page reuses validation/human/template.html
with a third set and question Q6.
"""
import csv, json, pathlib, random, collections

ROOT = pathlib.Path(__file__).resolve().parents[2]
V = ROOT / "validation"
OUT = pathlib.Path(__file__).resolve().parent
rng = random.Random(20261109)

# ---------- strata from the LLM labels ----------
included = {r["sha"] for r in csv.DictReader(open(ROOT / "data/processed/commits_lineages.csv"))}
edits = collections.defaultdict(set)
for e in csv.DictReader(open(ROOT / "data/processed/repair_edits.csv")):
    edits[e["sha"]].add(e["direction"])
key1 = {r["item_id"]: r for r in csv.DictReader(open(V / "sample_key.csv"))}
adj = {r["item_id"]: r for r in csv.DictReader(open(V / "adjudicated.csv"))}
s1 = {json.loads(l)["item_id"]: json.loads(l) for k in range(1, 5) for l in open(V / f"coding_batch_0{k}.jsonl")}
pin_ling = sorted(i for i in s1 if key1[i]["sample"] == "included" and key1[i]["sha"] in included and adj[i]["genuine"] == "YES"
                  and edits[key1[i]["sha"]] == {"MACHINE_PINNING"} and adj[i]["role"] in ("LINGUISTIC", "MIXED"))
L = V / "ling"
rd = lambda f: {r["item_id"]: {k: (r[k] or "").strip().upper() for k in ("role", "change")} for r in csv.DictReader(open(L / f))}
A, B = rd("coder_A.csv"), rd("coder_B.csv")
fin = {i: A[i] for i in A if A[i] == B[i]}; fin.update(rd("adjudicated_disagreements.csv"))
key2 = {r["item_id"]: r["sha"] for r in csv.DictReader(open(L / "key.csv"))}
s2 = {json.loads(l)["item_id"]: json.loads(l) for l in open(L / "items.jsonl")}
aware_mach = sorted(i for i in s2 if fin[i]["change"] == "LOCALE_AWARE" and fin[i]["role"] in ("MACHINE", "MIXED"))
assert (len(pin_ling), len(aware_mach)) == (15, 40), (len(pin_ling), len(aware_mach))
rest_pool = sorted([("1", i) for i in s1 if i not in pin_ling] + [("2", i) for i in s2 if i not in aware_mach])
rest = rng.sample(rest_pool, 105)
chosen = [("2", i, "S2_AWARE_MACHINE", len(aware_mach)) for i in aware_mach] + \
         [("1", i, "S1_PIN_LING", len(pin_ling)) for i in pin_ling] + \
         [(s, i, "REST", len(rest_pool)) for s, i in rest]
rng.shuffle(chosen)
s3 = [json.loads(l) for l in open(OUT / "set3_items.jsonl")]
strata3 = {r["sha"]: (r["stratum"], r["stratum_size"]) for r in csv.DictReader(open(OUT / "set3_sample.csv"))}
rng.shuffle(s3)

items, key = [], []
na = nb = 0
for s, i, st, size in chosen:
    if s == "1":
        na += 1; hid = f"A{na:03d}"; it = s1[i]; sha = key1[i]["sha"]
        items.append({"id": hid, "set": 1, "repo": it["repo"], "sha": sha, "message": it["message"], "patch": it["patch_excerpt"]})
    else:
        nb += 1; hid = f"B{nb:03d}"; it = s2[i]; sha = key2[i]
        cl = it["changed_lines"] if isinstance(it["changed_lines"], list) else []
        items.append({"id": hid, "set": 2, "repo": it["repo"], "sha": sha, "message": it["message"],
                      "edits": [{"file": c.get("file", ""), "removed": c.get("removed", ""), "added": c.get("added", "")} for c in cl],
                      "patch": it["patch_excerpt"]})
    key.append({"human_id": hid, "set": s, "orig_id": i, "sha": sha, "stratum": st, "stratum_size": size})
for n, it in enumerate(s3, 1):
    hid = f"C{n:03d}"; st, size = strata3[it["sha"]]
    items.append({"id": hid, "set": 3, "repo": it["repo"], "sha": it["sha"], "message": it["message"], "files": it["files"],
                  "tests": it["tests"], "patch": it["patch"]})
    key.append({"human_id": hid, "set": "3", "orig_id": "", "sha": it["sha"], "stratum": st, "stratum_size": size})

with open(OUT / "key_r4.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(key[0])); w.writeheader(); w.writerows(key)

# ---------- page: template of round 3 plus Set 3 and Q6 ----------
T = (V / "human/template.html").read_text()
REPL = [
    ('const STORE = "localehazard-human-coding-v1";', 'const STORE = "localehazard-human-coding-r4";'),
    ('    {k: "fit", t: "Q5 Uygunluk", sub: "yeni davranış bu kullanıma uygun mu?", o: ["FIT", "MISFIT", "NEUTRAL", "CANNOT_TELL"], need: a => !!a.change && a.change !== "OTHER"},\n  ],\n};',
     '    {k: "fit", t: "Q5 Uygunluk", sub: "yeni davranış bu kullanıma uygun mu?", o: ["FIT", "MISFIT", "NEUTRAL", "CANNOT_TELL"], need: a => !!a.change && a.change !== "OTHER"},\n  ],\n'
     '  3: [\n    {k: "loctest", t: "Q6 Yerel test", sub: "commit, onarılan işlemin locale gereksinimini kuran, doğrulayan veya çalıştıran bir test ekliyor ya da değiştiriyor mu?", o: ["YES", "NO", "UNCLEAR"]},\n  ],\n};'),
    ('"family", "fit", "note", "complete", "updated_at"', '"family", "fit", "loctest", "note", "complete"'),
    ('Object.assign({}, state.answers[it.id], patch, {updated_at: new Date().toISOString()})',
     'Object.assign({}, state.answers[it.id], patch)'),
    ('cur: {1: 0, 2: 0}', 'cur: {1: 0, 2: 0, 3: 0}'),
    ('const bySet = {1: ITEMS.filter(i => i.set === 1), 2: ITEMS.filter(i => i.set === 2)};',
     'const bySet = {1: ITEMS.filter(i => i.set === 1), 2: ITEMS.filter(i => i.set === 2), 3: ITEMS.filter(i => i.set === 3)};'),
    ('<button data-set="2">Set 2</button></div>', '<button data-set="2">Set 2</button><button data-set="3">Set 3</button></div>'),
    ('  const s1 = bySet[1].filter(i => status(i) === "ok").length, s2 = bySet[2].filter(i => status(i) === "ok").length;\n'
     '  document.getElementById("setinfo").textContent = `Set 1: ${s1}/${bySet[1].length} · Set 2: ${s2}/${bySet[2].length} tamam`;\n'
     '  const done = s1 + s2;',
     '  const sd = [1, 2, 3].map(s => bySet[s].filter(i => status(i) === "ok").length);\n'
     '  document.getElementById("setinfo").textContent = [1, 2, 3].map(s => `Set ${s}: ${sd[s - 1]}/${bySet[s].length}`).join(" · ") + " tamam";\n'
     '  const done = sd[0] + sd[1] + sd[2];'),
    ('for (const s of [state.set, 3 - state.set]) {', 'for (const s of [0, 1, 2].map(x => ((state.set - 1 + x) % 3) + 1)) {'),
    ('for (const k of ["genuine", "change", "role", "trigger", "family", "fit", "note", "updated_at"])',
     'for (const k of ["genuine", "change", "role", "trigger", "family", "fit", "loctest", "note"])'),
    ('    ${edits}\n',
     '    ${edits}\n    ${it.tests ? `<div class="card"><div class="small" style="margin-bottom:6px">Test yolu kuralına uyan dosyalara eklenen satırlar (dosya başına en çok 60)</div>${it.tests.length ? it.tests.map(t => `<div class="small">${esc(t.file)}</div><pre class="diff">${t.added.map(l => `<span class="a">+${esc(l)}</span>`).join("") || "<span>(eklenen satır yok)</span>"}</pre>`).join("") : `<div class="small">Bu commit test yolu kuralına uyan bir dosyayı değiştirmiyor. Değişen dosyalar: ${esc((it.files || []).join(", "))}</div>`}</div>` : ""}\n'),
    ('<p><strong>Set 1</strong> (210 öğe): soruların tamamı. <strong>Set 2</strong> (181 öğe): yalnızca değişiklik türü, rol ve uygunluk; bu öğelerde sınıflandırıcının eşleştirdiği satırlar ayrıca gösterilir.</p>',
     f'<p><strong>Set 1</strong> ({na} öğe): soruların tamamı. <strong>Set 2</strong> ({nb} öğe): yalnızca değişiklik türü, rol ve uygunluk; bu öğelerde sınıflandırıcının eşleştirdiği satırlar ayrıca gösterilir. <strong>Set 3</strong> ({len(s3)} öğe): yalnızca Q6; test dosyalarına eklenen satırlar ayrıca gösterilir.</p>'),
    ('      </dl>',
     '        <dt>Q6 Yerel test (Set 3)</dt>\n        <dd><code>YES</code>: commit, onarılan metin işleminin locale davranışını sınayan bir test ekliyor veya değiştiriyor: testte Türkçe/Azerice/Litvanca (ya da başka bir) varsayılan locale kuruluyor, <code>LC_ALL</code>/<code>LANG</code> ayarlanıyor, locale\'e duyarlı girdiyle (ör. <code>İ</code>, <code>ı</code>) beklenen sonuç doğrulanıyor. <code>NO</code>: test yok, ya da test locale gereksinimiyle ilgisiz (ör. yalnızca metinde "Turkey" geçen bir veri satırı, ilgisiz bir <code>LANG=</code> satırı). <code>UNCLEAR</code>: gösterilen satırlardan karar verilemiyor; gerekirse <em>GitHub\'da aç</em> ile commit\'e bakın.</dd>\n      </dl>'),
]
for a, b in REPL:
    assert T.count(a) == 1, a[:70]
    T = T.replace(a, b)
data = json.dumps(items, ensure_ascii=False).replace("</", "<\\/")
html = T.replace("__DATA__", data)
(OUT / "template_r4.html").write_text(T)
(OUT / "human_coding_r4.html").write_text(html.replace("__CODER__", ""))
(OUT / "for_coders").mkdir(exist_ok=True)
for n, coder in ((1, "H1"), (2, "H2")):
    (OUT / "for_coders" / f"degerlendirici_{n}.html").write_text(html.replace("__CODER__", coder))
print(json.dumps({"items": len(items), "set1": na, "set2": nb, "set3": len(s3),
                  "strata": dict(collections.Counter(k["stratum"] for k in key))}, indent=1))
