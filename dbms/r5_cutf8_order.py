"""Round 5 (short PostgreSQL paper): does the libc C.UTF-8 sort order change across Ubuntu releases?

Post hoc (protocol/DEVIATIONS.md, 2026-11-15). PostgreSQL 18.6 compares text with strcoll() for a libc collation
named C.UTF-8 (collate_is_c holds only for C and POSIX) but records no collation version for it, so a change of
its order is never reported. Debian and Ubuntu shipped their own C.UTF-8 before glibc 2.35 added one upstream.
This script sorts the same strings with the sort program, C library and C.UTF-8 locale of Ubuntu 18.04 (glibc 2.27),
20.04 (glibc 2.31) and 22.04 (glibc 2.35), each run through its own dynamic loader, and compares the orders with
each other and with code-point order. Inputs: the synthetic and dictionary datasets of the drift experiment, and a
seeded set of strings that mixes ASCII with BMP and supplementary-plane code points.
Usage: python3 dbms/r5_cutf8_order.py OUTDIR
"""
import csv, hashlib, json, pathlib, random, subprocess, sys, unicodedata

H = pathlib.Path(__file__).resolve().parent
OUTDIR = pathlib.Path(sys.argv[1]).resolve()
OUTDIR.mkdir(parents=True, exist_ok=True)
ROOTS = {"18.04": H / "bionic", "20.04": H / "rootfs" / "focal", "22.04": H / "rootfs" / "jammy"}
SEED = 20261115
RANGES = [(0x21, 0x7E), (0xA1, 0x17F), (0x370, 0x3FF), (0x4E00, 0x9FFF), (0xAC00, 0xD7A3), (0xE000, 0xF8FF),
          (0xFB00, 0xFFFD), (0x10000, 0x1FFFF), (0x1F300, 0x1FAFF), (0x20000, 0x2A6DF)]


def mixed_strings(n=20000):
    rng = random.Random(SEED)
    out = set()
    while len(out) < n:
        chars = []
        for _ in range(rng.randint(1, 6)):
            if rng.random() < 0.5:
                chars.append(chr(rng.randint(0x61, 0x7A)))
            else:
                lo, hi = rng.choice(RANGES)
                chars.append(chr(rng.randint(lo, hi)))
        s = "".join(chars)
        if "\n" not in s and "\r" not in s:
            out.add(s)
    return sorted(out)


def ld_and_libpath(root):
    lib = root / "lib/x86_64-linux-gnu"
    ld = sorted(lib.glob("ld-2.*.so")) or sorted((root / "usr/lib/x86_64-linux-gnu").glob("ld-linux-x86-64.so.2"))
    return ld[0], f"{lib}:{root / 'usr/lib/x86_64-linux-gnu'}"


def run_tool(root, args, inp=None):
    ld, lp = ld_and_libpath(root)
    env = {"LOCPATH": str(root / "usr/lib/locale"), "LC_ALL": "C.UTF-8", "PATH": "/usr/bin:/bin"}
    return subprocess.run([str(ld), "--library-path", lp] + args, input=inp, capture_output=True, env=env,
                          text=True, encoding="utf-8")


def distro_sorted(root, words):
    r = run_tool(root, [str(root / "usr/bin/sort")], "\n".join(words) + "\n")
    if r.returncode != 0:
        raise RuntimeError(r.stderr)
    return r.stdout.split("\n")[:-1]


def strings_moved(a, b):
    """Fewest strings whose removal leaves a and b in the same order: n minus the longest common subsequence."""
    import bisect
    rb = {s: i for i, s in enumerate(b)}
    tails = []
    for x in a:
        k = bisect.bisect_left(tails, rb[x])
        tails[k:k + 1] = [rb[x]]
    return len(a) - len(tails)


def compare(a, b):
    rb = {s: i for i, s in enumerate(b)}
    return {"positions_differing": sum(x != y for x, y in zip(a, b)),
            "adjacent_pairs_inverted": sum(rb[x] > rb[y] for x, y in zip(a, a[1:])),
            "strings_moved": strings_moved(a, b)}


def main():
    sets = {}
    for ds in ("synthetic", "dictionary"):
        sets[ds] = [r[1] for r in csv.reader(open(H / f"results/raw_{ds}/dataset.csv", encoding="utf-8"))]
    mixed = mixed_strings()
    sets["mixed_planes"] = mixed
    # strata of the mixed set; "unassigned" means general category Cn in Python's Unicode database
    unassigned = lambda s: any(unicodedata.category(c) == "Cn" for c in s)
    supplementary = lambda s: any(ord(c) > 0xFFFF for c in s)
    sets["mixed_bmp_assigned"] = [s for s in mixed if not unassigned(s) and not supplementary(s)]
    sets["mixed_supplementary_assigned"] = [s for s in mixed if not unassigned(s) and supplementary(s)]
    sets["mixed_with_unassigned"] = [s for s in mixed if unassigned(s)]
    res = {"meta": {"seed": SEED, "ranges": [[hex(a), hex(b)] for a, b in RANGES],
                    "python_unicode_version": unicodedata.unidata_version}}
    for rel, root in ROOTS.items():
        loc = run_tool(root, [str(root / "usr/bin/locale")])
        ld, _ = ld_and_libpath(root)
        res["meta"][rel] = {"loader": ld.name, "locale_stderr": loc.stderr.strip(),
                            "locale_dirs": sorted(p.name for p in (root / "usr/lib/locale").iterdir())}
    for name, words in sets.items():
        orders = {rel: distro_sorted(root, words) for rel, root in ROOTS.items()}
        cp = sorted(words)  # Python str order is code-point order
        for rel, o in orders.items():
            assert sorted(o) == sorted(words), f"{rel} lost or changed strings in {name}"
        r = {"n": len(words), "sha256": hashlib.sha256("\n".join(words).encode()).hexdigest()}
        for rel, o in orders.items():
            r[f"{rel}_vs_codepoint"] = compare(o, cp)
        r["18.04_vs_20.04"] = compare(orders["18.04"], orders["20.04"])
        r["20.04_vs_22.04"] = compare(orders["20.04"], orders["22.04"])
        r["18.04_vs_22.04"] = compare(orders["18.04"], orders["22.04"])
        diff = [(x, y) for x, y in zip(orders["20.04"], orders["22.04"]) if x != y][:20]
        r["examples_20.04_vs_22.04"] = [[x.encode("unicode_escape").decode(), y.encode("unicode_escape").decode()]
                                        for x, y in diff]
        res[name] = r
        print(name, json.dumps({k: v for k, v in r.items() if not k.startswith("examples")}), flush=True)
    (OUTDIR / "r5_cutf8_order.json").write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
