"""Round 5: LaTeX macros and tables for the short PostgreSQL paper.

Reads the round-4 drift results (dbms/results/dbms_results_*.json) and the round-5 results (results/r5/*), and
writes OUTDIR/numbers_r5.tex, OUTDIR/tab_drift.tex and OUTDIR/tab_turkish.tex. Every value is read from a file.
Usage: python3 src/r5_numbers.py OUTDIR
"""
import json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = pathlib.Path(sys.argv[1]).resolve()
OUT.mkdir(parents=True, exist_ok=True)
R5 = ROOT / "results" / "r5"
load = lambda p: json.load(open(p, encoding="utf-8"))
EMU = {ds: load(ROOT / f"dbms/results/dbms_results_{ds}.json") for ds in ("synthetic", "dictionary")}
REP = {ds: load(R5 / f"repair_{ds}/r5_repair_{ds}.json") for ds in ("synthetic", "dictionary")}
TUR = load(R5 / "turkish/r5_turkish.json")
ORD = load(R5 / "cutf8_order/r5_cutf8_order.json")
REAL = load(R5 / "real_upgrade/r5_real_upgrade.json")
N = {}


def fmt(x):
    return f"{x:,}" if isinstance(x, int) else x


def pct(a, b):
    return f"{100 * a / b:.1f}"


def emu(ds, cond, db="libc_en"):
    d = EMU[ds][cond][db]
    return {"warn": d["connect_warning"], "amcheck": d["amcheck_parent_check_ok"],
            "miss": d["seq_point_hits"] - d["index_point_hits"], "lookups": d["lookups"],
            "rng": d["range_count_mismatches"], "ne": d["nonempty_ranges"], "dup": d["duplicate_keys_admitted"]}


def real(path, db):
    d = REAL[path][db]
    return {"warn": d["connect_warning"], "amcheck": d["amcheck_parent_ok"], "miss": d["missed_lookups"],
            "lookups": d["lookups"], "rng": d["range_mismatches"], "ne": d["nonempty_ranges"], "dup": d["duplicate_keys"],
            "rec": d["recorded_collversion"], "act": d["actual_collversion"]}


# --- RQ1: drift, emulated (round 4) and real (round 5)
for ds, tag in (("synthetic", "Syn"), ("dictionary", "Dic")):
    rows = EMU[ds]["meta"]["rows"]
    N[f"Rf{tag}Rows"] = rows
    e = emu(ds, "drift")
    N[f"Rf{tag}Miss"], N[f"Rf{tag}MissPct"] = e["miss"], pct(e["miss"], e["lookups"])
    N[f"Rf{tag}RangeBad"], N[f"Rf{tag}NonEmpty"], N[f"Rf{tag}RangePct"] = e["rng"], e["ne"], pct(e["rng"], e["ne"])
    N[f"Rf{tag}Dup"], N[f"Rf{tag}DupPct"] = e["dup"], pct(e["dup"], rows)
    r = real("bionic_to_focal", "en_syn" if ds == "synthetic" else "en_dic")
    N[f"Rf{tag}RealSame"] = "yes" if (r["miss"], r["rng"], r["dup"]) == (e["miss"], e["rng"], e["dup"]) else "no"
    for p, rep in REP[ds].items():
        if p == "meta":
            continue
        a = rep["after"]
        N[f"Rf{tag}{p.capitalize()}Miss"] = a["missed_lookups"]
        N[f"Rf{tag}{p.capitalize()}Reins"] = rep["after_reinsert"]["accepted"]
        N[f"Rf{tag}{p.capitalize()}Amcheck"] = "pass" if a["amcheck_parent_ok"] else "fail"
        N[f"Rf{tag}{p.capitalize()}Warn"] = "yes" if a["connect_warning"] else "no"
    N[f"Rf{tag}DirtyDeleted"] = REP[ds]["dirty"]["dedup_deleted_rows"]
    N[f"Rf{tag}DirtyReindexWithDups"] = "failed" if not REP[ds]["dirty"]["reindex_with_dups_ok"] else "succeeded"
N["RfLookups"] = EMU["synthetic"]["drift"]["libc_en"]["lookups"]
N["RfRanges"] = EMU["synthetic"]["drift"]["libc_en"]["ranges"]

m = real("focal_to_jammy", "cutf8_mixed")
N["RfMixedRows"] = REAL["meta"]["datasets"]["mixed"]["rows"]
N["RfMixedMiss"], N["RfMixedMissPct"] = m["miss"], pct(m["miss"], m["lookups"])
N["RfMixedRangeBad"], N["RfMixedNonEmpty"] = m["rng"], m["ne"]
N["RfMixedDup"], N["RfMixedDupPct"] = m["dup"], pct(m["dup"], N["RfMixedRows"])
for rel, lines in REAL["meta"]["images"].items():
    word = {"18.04": "OneEightZeroFour", "20.04": "TwoZeroZeroFour", "22.04": "TwoTwoZeroFour"}[rel]
    N[f"RfGlibc{word}"] = lines[0].split()[-1]

# --- C.UTF-8 order across Ubuntu releases
N["RfUnicodeVersion"] = ORD["meta"]["python_unicode_version"]
for key, tag in (("synthetic", "Syn"), ("dictionary", "Dic"), ("mixed_planes", "Mixed"),
                 ("mixed_bmp_assigned", "MixedBmp"), ("mixed_supplementary_assigned", "MixedSupp"),
                 ("mixed_with_unassigned", "MixedUnas")):
    o = ORD[key]
    N[f"RfOrd{tag}N"] = o["n"]
    N[f"RfOrd{tag}Moved"] = o["20.04_vs_22.04"]["strings_moved"]
    N[f"RfOrd{tag}MovedEighteen"] = o["18.04_vs_20.04"]["strings_moved"]

# --- RQ2: Turkish case mapping
DBS = [d for d in TUR if d != "meta"]
PAIRS = list(TUR["meta"]["pairs"])
MECHS = list(TUR["meta"]["mechanisms"])
TR = ["tr_libc", "tr_icu", "tr_coll_c_ctype"]
same_tr = all(TUR[a][f"{mm}|{p}"]["second_accepted"] == TUR["tr_libc"][f"{mm}|{p}"]["second_accepted"]
              for a in TR for mm in MECHS for p in PAIRS)
N["RfTrDbsIdentical"] = "yes" if same_tr else "no"
N["RfTurkishMechanisms"] = len(MECHS)
N["RfTurkishDbs"] = len(DBS)
errors = sum(1 for d in DBS for mm in MECHS for p in PAIRS if TUR[d][f"{mm}|{p}"]["second_accepted"] is None)
N["RfTurkishErrors"] = errors
ok_ascii_tr = [mm for mm in MECHS if TUR["tr_libc"][f"{mm}|ascii_email"]["second_accepted"] is False]
N["RfTrAsciiKept"] = len(ok_ascii_tr)
both = [(d, mm) for d in DBS for mm in MECHS if all(TUR[d][f"{mm}|{p}"]["second_accepted"] is False for p in PAIRS)]
N["RfAllPairsKept"] = len(both)

with open(OUT / "numbers_r5.tex", "w", encoding="utf-8") as fh:
    fh.write("% Generated by src/r5_numbers.py from dbms/results and results/r5. Do not edit.\n")
    for k, v in sorted(N.items()):
        fh.write(f"\\providecommand{{\\{k}}}{{{fmt(v)}}}\n")

# --- Table: drift outcomes
def cell(a, b=None, key="miss"):
    return fmt(a[key]) if b is None else f"{fmt(a[key])} / {fmt(b[key])}"


def yn(x):
    return "yes" if x else "no"


lines = []
def row(label, ver, a, b=None):
    amc = "pass" if a["amcheck"] and (b is None or b["amcheck"]) else "fail"
    lines.append(f"{label} & {ver} & {yn(a['warn'])} & {amc} & {cell(a, b)} & {cell(a, b, 'rng')} & {cell(a, b, 'dup')} \\\\")

row("Emulated, 2.27 $\\to$ 2.43 data", "2.27 $\\to$ 2.43", emu("synthetic", "drift"), emu("dictionary", "drift"))
row("Emulated, 2.27 $\\to$ 2.28 data", "2.27 $\\to$ 2.28", emu("synthetic", "drift228"), emu("dictionary", "drift228"))
row("Emulated, 2.27 $\\to$ 2.43 data", "2.27 $\\to$ 2.27", emu("synthetic", "silent"), emu("dictionary", "silent"))
row("Ubuntu 18.04 $\\to$ 20.04, en\\_US", "2.27 $\\to$ 2.31", real("bionic_to_focal", "en_syn"), real("bionic_to_focal", "en_dic"))
row("Ubuntu 20.04 $\\to$ 22.04, en\\_US", "2.31 $\\to$ 2.35", real("focal_to_jammy", "en_syn"), real("focal_to_jammy", "en_dic"))
row("Ubuntu 20.04 $\\to$ 22.04, C.UTF-8$^{a}$", "none", real("focal_to_jammy", "cutf8_mixed"))
controls = [emu(ds, c, db) for ds in EMU for c, db in (("stable", "libc_en"), ("drift", "icu_en"), ("drift", "c_coll"))]
controls += [real(p, db) for p in ("focal_restart", "bionic_to_focal", "focal_to_jammy")
             for db in ("en_syn", "en_dic", "cutf8_syn", "cutf8_mixed", "c_syn")
             if p == "focal_restart" or db in ("c_syn", "cutf8_syn") or (p == "bionic_to_focal" and db == "cutf8_mixed")]
clean = all(c["amcheck"] and c["miss"] == 0 and c["rng"] == 0 and c["dup"] == 0 for c in controls)
N_CONTROLS = len(controls)
lines.append(f"Controls$^{{b}}$ ({N_CONTROLS} databases) & & & {'pass' if clean else 'fail'} & 0 & 0 & 0 \\\\" if clean
             else "Controls$^{b}$ & & & see results file & & & \\\\")
tab = ("\\begin{table}[t]\n\\centering\\footnotesize\n\\setlength{\\tabcolsep}{3pt}\n"
       "\\caption{Index damage in PostgreSQL~18.6 after the collation data under an existing unique index changed.}\n"
       "\\label{tab:drift}\n\\begin{tabular}{@{}llllrrr@{}}\n\\toprule\n"
       "Change of collation data & Version & Warning & amcheck & Missed lookups & Wrong ranges & Duplicates \\\\\n\\midrule\n"
       + "\n".join(lines) + "\n\\bottomrule\n\\end{tabular}\n\n\\smallskip\\footnotesize\n"
       f"Version: the glibc version that PostgreSQL saw before and after. Cells give synthetic / word-list values: missed lookups among {fmt(N['RfLookups'])} existing keys, wrong range counts among the non-empty ones of {fmt(N['RfRanges'])}, and accepted re-inserted keys. "
       f"$^{{a}}$Mixed-plane strings ({fmt(N['RfMixedRows'])}). "
       "$^{b}$Unchanged data, ICU and C collations, a restart without upgrade, and C.UTF-8 databases whose order did not change.\n"
       "\\end{table}\n")
(OUT / "tab_drift.tex").write_text(tab, encoding="utf-8")
with open(OUT / "numbers_r5.tex", "a", encoding="utf-8") as fh:
    fh.write(f"\\providecommand{{\\RfControls}}{{{N_CONTROLS}}}\n")

# --- Table: Turkish matrix (= : the second key was rejected, so the pair counts as one key)
COLS = [("tr_libc", "\\shortstack{Turkish\\\\ctype$^{a}$}"), ("en_libc", "\\shortstack{libc\\\\en\\_US}"),
        ("builtin_c", "\\shortstack{builtin\\\\C.UTF-8}"), ("builtin_unicode_fast", "\\shortstack{builtin\\\\UNICODE\\_FAST}")]
LABEL = {"lower_index": "\\texttt{lower(v)}", "upper_index": "\\texttt{upper(v)}", "casefold_index": "\\texttt{casefold(v)}",
         "citext_unique": "citext", "lower_arg_c": "\\texttt{lower(v COLLATE \"C\")}",
         "lower_result_c": "\\texttt{lower(v) COLLATE \"C\"}", "column_c_lower": "column \\texttt{\"C\"}, \\texttt{lower(v)}",
         "citext_column_c": "citext, column \\texttt{\"C\"}", "icu_und_ci": "ICU \\texttt{und-u-ks-level2}",
         "icu_tr_ci": "ICU \\texttt{tr-u-ks-level2}"}
sym = lambda v: "?" if v is None else ("$\\neq$" if v else "$=$")
body = []
for mm in MECHS:
    cells = [sym(TUR[db][f"{mm}|{p}"]["second_accepted"]) for db, _ in COLS for p in PAIRS]
    body.append(LABEL[mm] + " & " + " & ".join(cells) + " \\\\")
head1 = " & " + " & ".join(f"\\multicolumn{{3}}{{c}}{{{t}}}" for _, t in COLS) + " \\\\"
head2 = "Unique key & " + " & ".join(["A & D & T"] * len(COLS)) + " \\\\"
tab = ("\\begin{table}[t]\n\\centering\\small\n\\setlength{\\tabcolsep}{2.5pt}\n"
       "\\caption{Whether each unique key treats three case pairs as the same key, by database locale.}\n"
       "\\label{tab:turkish}\n\\begin{tabular}{@{}l" + ">{\\centering\\arraybackslash}p{1.3em}" * (3 * len(COLS)) + "@{}}\n\\toprule\n" + head1 + "\n"
       + "".join(f"\\cmidrule(lr){{{2 + 3 * i}-{4 + 3 * i}}}" for i in range(len(COLS))) + "\n" + head2 + "\n\\midrule\n"
       + "\n".join(body) + "\n\\bottomrule\n\\end{tabular}\n\n\\smallskip\\footnotesize\n"
       "A: \\texttt{admin@example.org} / \\texttt{ADMIN@EXAMPLE.ORG}; D: \\textit{ışık} / \\textit{IŞIK}; T: \\textit{istanbul} / \\textit{İSTANBUL}. "
       "$=$: the second key was rejected; $\\neq$: it was accepted. "
       "$^{a}$Identical in the libc tr\\_TR, ICU tr, and C-collation-with-tr\\_TR-ctype databases.\n\\end{table}\n")
(OUT / "tab_turkish.tex").write_text(tab, encoding="utf-8")
print(json.dumps(N, indent=0, ensure_ascii=False))
