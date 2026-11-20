"""Validate emulated glibc 2.27 collation (2.27 sources compiled/run by host glibc 2.43) against a real glibc 2.27
runtime (Ubuntu 18.04 libc 2.27 + localedef + coreutils sort). Also compare the 2.28 sources and host 2.43 data."""
import csv, json, os, pathlib, subprocess, sys, functools, locale
H = pathlib.Path(__file__).resolve().parent; OUT = H / "results/emulation"; OUT.mkdir(parents=True, exist_ok=True)
B = H / "bionic"; LD = B / "lib/x86_64-linux-gnu/ld-2.27.so"; LP = f"{B}/lib/x86_64-linux-gnu:{B}/usr/lib/x86_64-linux-gnu"
def host_sorted(words, locdir):
    code = ("import sys,locale,functools;locale.setlocale(locale.LC_ALL,'en_US.UTF-8');"
            "w=sys.stdin.read().split('\\n')[:-1];w.sort(key=functools.cmp_to_key(lambda a,b: locale.strcoll(a,b) or ((a>b)-(a<b))));"
            "sys.stdout.write('\\n'.join(w)+'\\n')")
    r = subprocess.run([sys.executable, "-c", code], input="\n".join(words) + "\n", capture_output=True, text=True,
                       env={"LOCPATH": str(H / "loc" / locdir), "PATH": "/usr/bin"})
    return r.stdout.split("\n")[:-1]
def real227_sorted(words):
    r = subprocess.run([str(LD), "--library-path", LP, str(B / "usr/bin/sort")], input="\n".join(words) + "\n", capture_output=True,
                       text=True, env={"LOCPATH": str(H / "loc/bionic"), "LC_ALL": "en_US.UTF-8"})
    return r.stdout.split("\n")[:-1]
res = {}
for ds in ("synthetic", "dictionary"):
    w = [r[1] for r in csv.reader(open(H / f"results/raw_{ds}/dataset.csv"))]
    real = real227_sorted(w); em = host_sorted(w, "old"); v228 = host_sorted(w, "v228"); new = host_sorted(w, "new")
    rank = lambda order: {s: i for i, s in enumerate(order)}
    def adj_agree(a, b):  # share of adjacent pairs of a that are in the same relative order in b
        rb = rank(b); return sum(rb[x] < rb[y] for x, y in zip(a, a[1:])) / (len(a) - 1)
    res[ds] = {"n": len(w), "real227_equals_emulated227": real == em, "positions_differing_real_vs_emulated": sum(x != y for x, y in zip(real, em)),
               "adjacent_pair_agreement_real_vs_emulated": round(adj_agree(real, em), 6),
               "positions_differing_real227_vs_243": sum(x != y for x, y in zip(real, new)),
               "positions_differing_228_vs_243": sum(x != y for x, y in zip(v228, new)),
               "positions_differing_real227_vs_228": sum(x != y for x, y in zip(real, v228))}
    print(ds, res[ds], flush=True)
json.dump(res, open(OUT / "emulation_check.json", "w"), indent=1)
