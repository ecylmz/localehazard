"""Figure 1: one API contract, two text roles. Values are computed, not typed."""
import pathlib, subprocess, json
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
ROOT = pathlib.Path(__file__).resolve().parents[1]
# compute the four outputs with Java (the frozen benchmark's Java contract)
src = ROOT / "figures/Fig1.java"
src.write_text('import java.util.Locale;public class Fig1{public static void main(String[] a){Locale tr=Locale.forLanguageTag("tr-TR");'
               'System.out.println("[\\""+"TITLE".toLowerCase(tr)+"\\",\\""+"TITLE".toLowerCase(Locale.ROOT)+"\\",\\""+"IŞIK".toLowerCase(tr)+"\\",\\""+"IŞIK".toLowerCase(Locale.ROOT)+"\\"]");}}')
out = json.loads(subprocess.run(["java", str(src)], capture_output=True, text=True).stdout)
mt, mr, lt, lr = out
INK, MUTED, BLUE, ORANGE, LINE = "#0b0b0b", "#52514e", "#2a78d6", "#eb6834", "#b9b8b3"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8})
fig, ax = plt.subplots(figsize=(7.0, 2.6)); ax.set_xlim(0, 11); ax.set_ylim(0.2, 4.0); ax.axis("off")
ax.text(4.55, 3.72, "toLowerCase(Locale tr-TR)\nTurkish-tailored mapping", ha="center", va="center", fontsize=8, color=INK, fontweight="bold")
ax.text(8.75, 3.72, "toLowerCase(Locale.ROOT)\nlocale-neutral mapping", ha="center", va="center", fontsize=8, color=INK, fontweight="bold")
rows = [("Machine text\n(protocol keyword)\nmust become “title”", "TITLE", mt, mt == "title", mr, mr == "title", 2.35),
        ("Linguistic text\n(Turkish word ‘light’)\nmust become “ışık”", "IŞIK", lt, lt == "ışık", lr, lr == "ışık", 0.85)]
for lab, inp, o1, ok1, o2, ok2, y in rows:
    ax.text(0.05, y, lab, ha="left", va="center", fontsize=7.6, color=INK, linespacing=1.35)
    for x, o, ok in ((4.55, o1, ok1), (8.75, o2, ok2)):
        col = BLUE if ok else ORANGE
        ax.add_patch(FancyBboxPatch((x - 1.95, y - 0.55), 3.9, 1.1, boxstyle="round,pad=0.02,rounding_size=0.08", fc="white", ec=col, lw=1.4 if not ok else 1.0))
        ax.text(x - 1.75, y + 0.18, f"“{inp}” → “{o}”", ha="left", va="center", fontsize=10, family="DejaVu Sans Mono", color=INK)
        ax.text(x - 1.75, y - 0.27, ("✓ application-correct" if ok else "✗ contract-domain mismatch"), ha="left", va="center", fontsize=7.6, color=col, fontweight="bold")
fig.savefig(ROOT / "figures/fig_motivating.pdf", bbox_inches="tight"); fig.savefig(ROOT / "figures/fig_motivating.png", dpi=200, bbox_inches="tight")
print(out)
