"""Build the round-4 reconciliation page (validation/human_r4/for_coders/uzlasma.html).

Shows every item on which the two human coders' exports differ on a question of its set (the same rule as
disagreements_r4.csv), with the item content, both labels and both notes. The coders choose one label per differing
question together. The page exports a complete reconciled CSV (all items; agreed labels taken over unchanged; labels
of questions that no longer apply under the reconciled answers are cleared) in the column format of the coding
export, for analyze_human_r4.py. No model label, stratum or aggregate is embedded.

Usage: python3 validation/human_r4/build_reconcile_page_r4.py H1.csv H2.csv
"""
import csv, json, pathlib, re, sys

H = pathlib.Path(__file__).resolve().parent
read = lambda p: {r["item_id"]: r for r in csv.DictReader(open(p, encoding="utf-8-sig"))}
h1, h2 = read(sys.argv[1]), read(sys.argv[2])
page = (H / "human_coding_r4.html").read_text()
m = re.search(r"const ITEMS = (\[.*?\]);\n", page, re.S)
assert m, "ITEMS not found in human_coding_r4.html"
items = json.loads(m.group(1).replace("<\\/", "</"))
QS = {"1": ["genuine", "role", "trigger", "family", "fit"], "2": ["change", "role", "fit"], "3": ["loctest"]}
F = ["genuine", "change", "role", "trigger", "family", "fit", "loctest", "note"]
assert {i["id"] for i in items} == set(h1) == set(h2)
lab = {i: {"H1": {k: h1[i].get(k, "") for k in F}, "H2": {k: h2[i].get(k, "") for k in F}} for i in h1}
dis = {i["id"]: [q for q in QS[str(i["set"])] if lab[i["id"]]["H1"][q] != lab[i["id"]]["H2"][q]] for i in items}
dis = {k: v for k, v in dis.items() if v}
show = [dict(i, labels=lab[i["id"]], differ=dis[i["id"]]) for i in items if i["id"] in dis]
agreed = {i: {q: lab[i]["H1"][q] for q in QS[str(next(x["set"] for x in items if x["id"] == i))]} for i in h1}
sets = {i["id"]: i["set"] for i in items}
data = json.dumps({"show": show, "agreed": agreed, "sets": sets}, ensure_ascii=False).replace("</", "<\\/")

HTML = r"""<!doctype html>
<html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>LocaleHazard uzlaşma</title>
<style>
:root{--bg:#f7f7f5;--card:#fff;--ink:#1d1d1b;--mute:#666;--line:#ddd;--add:#e6f4ea;--del:#fdecea;--h1:#2457a6;--h2:#a6243f;--ok:#2e7d32;--todo:#b26a00}
@media (prefers-color-scheme:dark){:root{--bg:#161616;--card:#212121;--ink:#eee;--mute:#aaa;--line:#3a3a3a;--add:#1f3a27;--del:#3e2020;--h1:#7fa8ef;--h2:#ef7f98;--ok:#7bc47f;--todo:#f0b04a}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.45 system-ui,sans-serif}
header{position:sticky;top:0;z-index:5;background:var(--card);border-bottom:1px solid var(--line);padding:10px 16px;display:flex;flex-wrap:wrap;gap:10px;align-items:center}
header h1{font-size:17px;margin:0 12px 0 0}button,select,textarea{font:inherit;color:inherit;background:var(--card);border:1px solid var(--line);border-radius:6px;padding:5px 9px}
button{cursor:pointer}main{max-width:1100px;margin:0 auto;padding:16px}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:14px;margin:0 0 16px}
.top{display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap}.small{color:var(--mute);font-size:13px}
pre{white-space:pre-wrap;word-break:break-word;font:12.5px/1.4 ui-monospace,Menlo,monospace;margin:6px 0;max-height:340px;overflow:auto;border:1px solid var(--line);border-radius:6px;padding:6px}
.a{background:var(--add);display:block}.d{background:var(--del);display:block}
table{border-collapse:collapse;width:100%;margin-top:10px}td,th{border-top:1px solid var(--line);padding:6px;vertical-align:top;text-align:left}
.c1{color:var(--h1);font-weight:600}.c2{color:var(--h2);font-weight:600}.diff td{background:rgba(255,200,0,.08)}
.st-ok{color:var(--ok)}.st-todo{color:var(--todo)}textarea{width:100%;min-height:48px}
details summary{cursor:pointer;color:var(--mute);font-size:13px}.guide{font-size:14px}
</style></head><body>
<header><h1>Uzlaşma (4. tur)</h1><span id="prog"></span>
<label class="small"><input type="checkbox" id="only"> yalnızca bitmemişler</label>
<button id="exp">Uzlaşılmış CSV dışa aktar</button><button id="imp">CSV içe aktar</button><input type="file" id="file" accept=".csv" hidden></header>
<main>
<div class="card guide">
<p>Bu sayfada iki kodlayıcının farklı cevap verdiği öğeler var. Diğer öğelerdeki ortak cevaplar değişmeden dışa aktarılır.</p>
<p>Her öğede farklı olan sorular sarı satırdadır. Öğeyi birlikte inceleyin ve kodlama kılavuzuna göre son cevabı seçin. Gerekirse <em>GitHub'da aç</em> ile commit'in tamamına bakın. Bir cevabı değiştirmenin nedenini "Uzlaşma notu" alanına kısaca yazın. Bir soru son cevaplara göre artık sorulmuyorsa (örneğin Q1 = NO ise Q2-Q5), o soru dışa aktarımda boş kalır.</p>
<p>Cevaplar bu tarayıcıda saklanır. Arada bir "Uzlaşılmış CSV dışa aktar" ile yedek alın. Bitince <code>human_coding_reconciled_&lt;tarih&gt;.csv</code> dosyasını gönderin.</p>
</div>
<div id="list"></div>
</main>
<script>
const DATA = __DATA__;
const OPTS = {genuine:["YES","NO","UNCLEAR"],change:["LOCALE_AWARE","UNICODE_FOLD","OTHER"],role:["MACHINE","LINGUISTIC","MIXED","UNCLEAR"],
  trigger:["OBSERVED_FAILURE","TOOL_DRIVEN","PREVENTIVE","UNCLEAR"],family:["F1","F2","F3","F4","F5","F6","OTHER"],
  fit:["FIT","MISFIT","NEUTRAL","CANNOT_TELL"],loctest:["YES","NO","UNCLEAR"]};
const NAMES = {genuine:"Q1 Gerçek mi?",change:"Değişiklik türü",role:"Q2 Rol",trigger:"Q3 Tetikleyici",family:"Q4 Senaryo ailesi",fit:"Q5 Uygunluk",loctest:"Q6 Yerel test"};
const QS = {1:["genuine","role","trigger","family","fit"],2:["change","role","fit"],3:["loctest"]};
const NEED = {1:{role:a=>a.genuine==="YES",trigger:a=>a.genuine==="YES",family:a=>a.genuine==="YES",fit:a=>a.genuine==="YES"},
  2:{role:a=>!!a.change&&a.change!=="OTHER",fit:a=>!!a.change&&a.change!=="OTHER"},3:{}};
const STORE = "localehazard-reconcile-r4";
let S = {};
try { S = JSON.parse(localStorage.getItem(STORE) || "{}") || {}; } catch (e) { S = {}; }
const save = () => { try { localStorage.setItem(STORE, JSON.stringify(S)); } catch (e) {} };
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const diff = t => esc(t).split("\n").map(l => l.startsWith("+") ? `<span class="a">${l}</span>` : l.startsWith("-") ? `<span class="d">${l}</span>` : l).join("\n");
function final(it) {  // reconciled answers of one shown item: agreed answers plus the chosen ones
  const a = {}, s = S[it.id] || {};
  for (const q of QS[it.set]) a[q] = it.differ.includes(q) ? (s[q] ?? null) : it.labels.H1[q];
  return a;
}
function open_(it) {  // differing questions that still need a choice
  const a = final(it), need = NEED[it.set];
  return it.differ.filter(q => a[q] === null && (!need[q] || [true].includes(need[q](Object.fromEntries(Object.entries(a).map(([k, v]) => [k, v ?? ""]))))));
}
function render() {
  const only = document.getElementById("only").checked;
  let done = 0;
  const html = DATA.show.map(it => {
    const left = open_(it); if (!left.length) done++;
    if (only && !left.length) return "";
    const a = final(it), s = S[it.id] || {};
    const rows = QS[it.set].map(q => {
      const d = it.differ.includes(q), h1 = it.labels.H1[q] || "(boş)", h2 = it.labels.H2[q] || "(boş)";
      const need = NEED[it.set][q], applies = !need || need(Object.fromEntries(Object.entries(a).map(([k, v]) => [k, v ?? ""])));
      const sel = d ? `<select data-id="${it.id}" data-q="${q}"><option value="">seçin</option>${OPTS[q].map(o => `<option${a[q] === o ? " selected" : ""}>${o}</option>`).join("")}<option value="__EMPTY__"${a[q] === "" ? " selected" : ""}>(boş bırak)</option></select>` : esc(a[q] || "(boş)");
      return `<tr class="${d ? "diff" : ""}"><td>${NAMES[q]}${applies ? "" : ' <span class="small">(son cevaplara göre sorulmuyor)</span>'}</td><td class="c1">${esc(h1)}</td><td class="c2">${esc(h2)}</td><td>${sel}</td></tr>`;
    }).join("");
    let body = "";
    if (it.edits && it.edits.length) body += `<div class="small">Sınıflandırıcının eşleştirdiği satırlar</div>` + it.edits.map(e => `<div class="small">${esc(e.file)}</div><pre>${e.removed ? `<span class="d">-${esc(e.removed)}</span>` : ""}${e.added ? `<span class="a">+${esc(e.added)}</span>` : ""}</pre>`).join("");
    if (it.tests) body += `<div class="small">Test yolu kuralına uyan dosyalara eklenen satırlar</div>` + (it.tests.length ? it.tests.map(t => `<div class="small">${esc(t.file)}</div><pre>${t.added.map(l => `<span class="a">+${esc(l)}</span>`).join("") || "(eklenen satır yok)"}</pre>`).join("") : `<div class="small">Test dosyası değişmiyor. Değişen dosyalar: ${esc((it.files || []).join(", "))}</div>`);
    if (it.patch) body += `<details><summary>Yama özeti</summary><pre>${diff(it.patch)}</pre></details>`;
    return `<div class="card" id="${it.id}"><div class="top"><div><strong>${it.id}</strong> · Set ${it.set} · ${esc(it.repo)} · <a href="https://github.com/${esc(it.repo)}/commit/${esc(it.sha)}" target="_blank" rel="noopener">GitHub'da aç</a></div>
      <div class="${left.length ? "st-todo" : "st-ok"}">${left.length ? "bekliyor: " + left.map(q => NAMES[q]).join(", ") : "tamam"}</div></div>
      <pre>${esc(it.message)}</pre>${body}
      <table><tr><th>Soru</th><th class="c1">H1</th><th class="c2">H2</th><th>Uzlaşılan</th></tr>${rows}</table>
      <p class="small"><span class="c1">H1 notu:</span> ${esc(it.labels.H1.note) || "-"}<br><span class="c2">H2 notu:</span> ${esc(it.labels.H2.note) || "-"}</p>
      <label class="small">Uzlaşma notu<textarea data-id="${it.id}" data-q="note">${esc(s.note || "")}</textarea></label></div>`;
  }).join("");
  document.getElementById("list").innerHTML = html || '<div class="card">Bitmemiş öğe kalmadı.</div>';
  document.getElementById("prog").textContent = `${done}/${DATA.show.length} öğe tamam`;
}
document.addEventListener("change", e => {
  const id = e.target.dataset.id, q = e.target.dataset.q; if (!id || q === "note") return;
  S[id] = S[id] || {}; const v = e.target.value;
  if (v === "") delete S[id][q]; else S[id][q] = v === "__EMPTY__" ? "" : v;
  save(); render();
});
document.addEventListener("input", e => {
  if (e.target.dataset.q !== "note") return; const id = e.target.dataset.id;
  S[id] = S[id] || {}; S[id].note = e.target.value; save();
});
document.getElementById("only").addEventListener("change", render);
const COLS = ["coder","set","item_id","genuine","change","role","trigger","family","fit","loctest","note","complete"];
const csvq = v => /[",\n\r]/.test(v) ? `"${v.replace(/"/g, '""')}"` : v;
document.getElementById("exp").addEventListener("click", () => {
  const shown = Object.fromEntries(DATA.show.map(it => [it.id, it]));
  const lines = [COLS.join(",")];
  for (const id of Object.keys(DATA.agreed).sort()) {
    const set = DATA.sets[id], it = shown[id];
    let a = it ? final(it) : {...DATA.agreed[id]}, complete = it ? (open_(it).length ? 0 : 1) : 1;
    const flat = Object.fromEntries(Object.entries(a).map(([k, v]) => [k, v ?? ""]));
    for (const [q, f] of Object.entries(NEED[set])) if (!f(flat)) flat[q] = "";
    const row = {coder: "RECONCILED", set: String(set), item_id: id, note: it ? ((S[id] || {}).note || "") : "", complete: String(complete)};
    lines.push(COLS.map(c => csvq(row[c] ?? flat[c] ?? "")).join(","));
  }
  const blob = new Blob(["﻿" + lines.join("\n") + "\n"], {type: "text/csv"});
  const url = URL.createObjectURL(blob), x = document.createElement("a");
  x.href = url; x.download = `human_coding_reconciled_${new Date().toISOString().slice(0, 10)}.csv`; x.click(); URL.revokeObjectURL(url);
});
function parseCSV(t) {
  const rows = []; let r = [], f = "", q = false;
  for (let i = 0; i < t.length; i++) { const c = t[i];
    if (q) { if (c === '"' && t[i + 1] === '"') { f += '"'; i++; } else if (c === '"') q = false; else f += c; }
    else if (c === '"') q = true; else if (c === ",") { r.push(f); f = ""; }
    else if (c === "\n" || c === "\r") { if (c === "\r" && t[i + 1] === "\n") i++; r.push(f); rows.push(r); r = []; f = ""; }
    else f += c; }
  if (f || r.length) { r.push(f); rows.push(r); }
  return rows;
}
document.getElementById("imp").addEventListener("click", () => document.getElementById("file").click());
document.getElementById("file").addEventListener("change", async e => {
  const f = e.target.files[0]; if (!f) return;
  const rows = parseCSV((await f.text()).replace(/^﻿/, "")); const h = rows.shift();
  const shown = Object.fromEntries(DATA.show.map(it => [it.id, it]));
  for (const r of rows) { const o = Object.fromEntries(h.map((k, i) => [k, r[i] ?? ""])); const it = shown[o.item_id]; if (!it) continue;
    S[it.id] = {note: o.note || ""};
    for (const q of it.differ) if (o[q] !== "" || o.complete === "1") S[it.id][q] = o[q]; }
  save(); render(); e.target.value = "";
});
render();
</script></body></html>
"""
out = H / "for_coders" / "uzlasma.html"
out.write_text(HTML.replace("__DATA__", data))
print(json.dumps({"items_shown": len(show), "questions": sum(len(v) for v in dis.values()),
                  "by_set": {s: sum(1 for x in show if str(x["set"]) == s) for s in "123"}}))
