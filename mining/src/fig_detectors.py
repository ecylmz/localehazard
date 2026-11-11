"""RQ4 figure: locale-relevant detector verdicts on role-paired probes (from results/detector_matrix.csv)."""
import csv, pathlib
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
ROOT = pathlib.Path(__file__).resolve().parents[1]
DET = ROOT / "detectors" if (ROOT.parent / "full_study").exists() else ROOT.parent / "analyzers"  # study / public layout
rows = list(csv.DictReader(open(DET / "results/detector_matrix.csv")))
tools = [("java","errorprone","Error Prone"),("java","spotbugs","SpotBugs"),("java","pmd","PMD"),("java","forbiddenapis","forbidden-apis"),
         ("dotnet","dotnet",".NET analyzers"),("go","govet","go vet"),("go","staticcheck","staticcheck"),("python","ruff","Ruff"),
         ("python","pylint","Pylint"),("js","eslint","ESLint"),("c","clang-tidy","clang-tidy"),("c","cppcheck","Cppcheck")]
probes = ["P1","P2","P3","P4","P5"]; roles = ["machine","linguistic"]
names = {"P1":"P1 default locale","P2":"P2 explicit tr-TR","P3":"P3 root/invariant","P4":"P4 culture equality","P5":"P5 culture key order"}
idx = {(r["language"], r["tool"], r["probe"], r["role"]): r for r in rows}
BLUE, INK, MUTED, GRID = "#2a78d6", "#0b0b0b", "#52514e", "#d9d8d4"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 7.5})
fig, ax = plt.subplots(figsize=(7.0, 4.3))
for j, (lang, tool, lab) in enumerate(tools):
    for i, p in enumerate(probes):
        for k, role in enumerate(roles):
            y = i * 2 + k
            r = idx.get((lang, tool, p, role))
            if r is None:
                ax.add_patch(Rectangle((j + 0.06, y + 0.06), 0.88, 0.88, facecolor="white", edgecolor=GRID, hatch="////", lw=0.4))
                continue
            cdm = r["label"] == "CDM"
            fc = BLUE if r["flagged"] == "1" else "white"
            ax.add_patch(Rectangle((j + 0.06, y + 0.06), 0.88, 0.88, facecolor=fc, edgecolor=MUTED if fc == "white" else BLUE, lw=0.6))
            if cdm:
                ax.plot(j + 0.5, y + 0.5, marker="x", ms=4.5, mew=1.2, color="white" if fc == BLUE else INK)
ax.set_xlim(0, len(tools)); ax.set_ylim(len(probes) * 2, 0)
ax.set_xticks([j + 0.5 for j in range(len(tools))]); ax.set_xticklabels([t[2] for t in tools], rotation=35, ha="right")
ax.set_yticks([i * 2 + k + 0.5 for i in range(len(probes)) for k in range(2)])
ax.set_yticklabels([f"{names[p]} · {r}" if k == 0 else r for p in probes for k, r in enumerate(roles)])
for i in range(1, len(probes)):
    ax.axhline(i * 2, color=MUTED, lw=0.8)
for x in (4, 5, 7, 9, 10):
    ax.axvline(x, color=MUTED, lw=0.8)
for s in ax.spines.values(): s.set_visible(False)
ax.tick_params(length=0)
from matplotlib.lines import Line2D
h = [Rectangle((0, 0), 1, 1, facecolor=BLUE, edgecolor=BLUE), Rectangle((0, 0), 1, 1, facecolor="white", edgecolor=MUTED),
     Line2D([], [], marker="x", ls="", color=INK, ms=5), Rectangle((0, 0), 1, 1, facecolor="white", edgecolor=GRID, hatch="////")]
ax.legend(h, ["flagged by a locale-relevant rule", "not flagged", "cell is a CDM under its stated role", "API not in the language's standard surface"],
          loc="lower center", bbox_to_anchor=(0.5, 1.06), ncol=2, frameon=False, fontsize=7, handlelength=1.2)
groups = [("Java", 0, 4), (".NET", 4, 5), ("Go", 5, 7), ("Python", 7, 9), ("JS", 9, 10), ("C", 10, 12)]
for name, a, b in groups:
    ax.text((a + b) / 2, -0.35, name, ha="center", va="bottom", fontsize=7.5, fontweight="bold", color=INK)
fig.subplots_adjust(left=0.265, right=0.99, top=0.8, bottom=0.2)
fig.savefig(ROOT / "figures/fig_detectors.pdf"); fig.savefig(ROOT / "figures/fig_detectors.png", dpi=200)
