"""RQ3 figure: lineages by ecosystem x operation (from results/rq3_mining.json)."""
import json, pathlib
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
ROOT = pathlib.Path(__file__).resolve().parents[1]
m = json.load(open(ROOT / "results/rq3_mining.json"))
cells = {tuple(k.split("|")): v for k, v in m["eco_op_commits"].items()}
ecos = [e for e, _ in sorted(m["ecosystem_commits"].items(), key=lambda kv: -kv[1])]
ops = [o for o in ["CASE", "COMPARE", "COLLATION", "CTYPE", "ENV"] if any((e, o) in cells for e in ecos)]
lab = {"jvm": "JVM (Java, Kotlin, ...)", "dotnet": ".NET", "js": "JavaScript/TS", "c_cpp": "C/C++", "python": "Python", "go": "Go",
       "rust": "Rust", "php": "PHP", "ruby": "Ruby", "shell_build": "Shell/build/CI", "sql": "SQL"}
opl = {"CASE": "case mapping", "COMPARE": "comparison", "COLLATION": "collation", "CTYPE": "char. class", "ENV": "process locale"}
mx = max(cells.values())
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8})
fig, ax = plt.subplots(figsize=(6.2, 0.32 * len(ecos) + 1.0))
import math
for i, e in enumerate(ecos):
    for j, o in enumerate(ops):
        v = cells.get((e, o), 0)
        if v:
            t = math.log10(v + 1) / math.log10(mx + 1)
            # single-hue sequential ramp (light -> dark blue)
            c = (1 - t * 0.85 * (1 - 0x2a / 255), 1 - t * 0.85 * (1 - 0x78 / 255), 1 - t * 0.85 * (1 - 0xd6 / 255))
            ax.add_patch(plt.Rectangle((j, i), 0.96, 0.92, color=c))
            ax.text(j + 0.48, i + 0.46, f"{v:,}", ha="center", va="center", fontsize=8, color="white" if t > 0.6 else "#0b0b0b")
        else:
            ax.text(j + 0.48, i + 0.46, "–", ha="center", va="center", color="#9a9994")
ax.set_xlim(0, len(ops)); ax.set_ylim(len(ecos), 0)
ax.set_xticks([j + 0.48 for j in range(len(ops))]); ax.set_xticklabels([opl[o] for o in ops])
ax.set_yticks([i + 0.46 for i in range(len(ecos))]); ax.set_yticklabels([f"{lab.get(e, e)}  ({m['ecosystem_commits'][e]:,})" for e in ecos])
ax.xaxis.tick_top(); ax.tick_params(length=0)
for sp in ax.spines.values(): sp.set_visible(False)
fig.tight_layout()
fig.savefig(ROOT / "figures/fig_mining.pdf"); fig.savefig(ROOT / "figures/fig_mining.png", dpi=200)
