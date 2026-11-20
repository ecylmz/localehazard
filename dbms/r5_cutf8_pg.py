"""Round 5 (short PostgreSQL paper): a real C.UTF-8 order change under a PostgreSQL index.

Post hoc (protocol/DEVIATIONS.md, 2026-11-16). r5_cutf8_order.py found that the libc C.UTF-8 order of Ubuntu
18.04 and 20.04 (Debian's C.UTF-8) differs from that of Ubuntu 22.04 (glibc's C.UTF-8, code-point order) for
strings with supplementary-plane, unassigned, and some BMP code points. This script runs the drift experiment of
run_dbms_experiment.py with that real change: a libc database with locale C.UTF-8 is loaded and indexed with the
C.UTF-8 locale files of Ubuntu 20.04 and restarted with those of Ubuntu 22.04, both loaded by the host C library
through LOCPATH. No version shim is used, because PostgreSQL records no version for a libc C.UTF-8 collation.
Validation: the host strcoll() order with each set of locale files must equal the order of that release's own
sort program on the same strings. A stable cluster (20.04 files before and after) is the control.
Data: the 20,000 seeded mixed-plane strings of r5_cutf8_order.py.
Usage: python3 dbms/r5_cutf8_pg.py OUTDIR
"""
import csv, hashlib, json, pathlib, subprocess, sys

OUTDIR = pathlib.Path(sys.argv[1]).resolve()
sys.argv = [sys.argv[0], "synthetic"]
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_dbms_experiment as m  # noqa: E402
import r5_cutf8_order as order  # noqa: E402

_env_for = m.env_for
LOC = {"focal": "../rootfs/focal/usr/lib/locale", "jammy": "../rootfs/jammy/usr/lib/locale"}


def _env_with_libs(locpath, shim):  # the build's RUNPATH points to an earlier checkout path
    e = _env_for(LOC.get(locpath, locpath), shim)
    e["LD_LIBRARY_PATH"] = str(m.HERE / "pg" / "lib")
    return e


m.env_for = _env_with_libs
OUTDIR.mkdir(parents=True, exist_ok=True)
m.RAW = OUTDIR / "raw_cutf8_pg"
m.RAW.mkdir(exist_ok=True)
DB = "cutf8"


def host_sorted(words, rel):
    code = ("import sys,locale,functools;locale.setlocale(locale.LC_ALL,'C.UTF-8');"
            "w=sys.stdin.read().split('\\n')[:-1];w.sort(key=functools.cmp_to_key(locale.strcoll));"
            "sys.stdout.write('\\n'.join(w)+'\\n')")
    r = subprocess.run([sys.executable, "-c", code], input="\n".join(words) + "\n", capture_output=True, text=True,
                       encoding="utf-8", env={"LOCPATH": str(HERE / "loc" / LOC[rel]), "PATH": "/usr/bin"})
    return r.stdout.split("\n")[:-1]


def phase1(cl, datafile):
    import shutil
    if cl.dir.exists():
        shutil.rmtree(cl.dir)
    cl.dir.parent.mkdir(exist_ok=True)
    e = m.env_for("focal", False)
    m.sh([str(m.PG / "initdb"), "-D", str(cl.dir), "--locale=C.UTF-8", "--encoding=UTF8", "-U", "postgres",
          "--no-instructions"], env=e)
    cl.start("focal", False)
    cl.psql("postgres", f"CREATE DATABASE {DB} TEMPLATE template0 LOCALE_PROVIDER libc LOCALE 'C.UTF-8' ENCODING 'UTF8'")
    cl.psql(DB, "CREATE EXTENSION amcheck")
    cl.psql(DB, "CREATE TABLE t(id int PRIMARY KEY, s text NOT NULL)")
    m.sh([str(m.PG / "psql"), "-X", "-p", str(cl.port), "-d", DB, "-v", "ON_ERROR_STOP=1", "-c",
          f"\\copy t(id,s) FROM '{datafile}' WITH (FORMAT csv)"], env=cl.env)
    cl.psql(DB, "CREATE UNIQUE INDEX t_s_uq ON t(s)")
    cl.psql(DB, "ANALYZE t")
    cl.psql(DB, "SELECT bt_index_parent_check('t_s_uq', true, true)", tag="p1_amcheck")
    cl.stop()


def phase2(cl, rel, rows):
    cl.start(rel, False)
    d = {}
    r = cl.psql(DB, "SELECT 1", tag="p2_connect")
    d["connect_warning"] = "collation version mismatch" in r.stderr
    d["recorded_collversion"] = cl.psql(DB, "SELECT quote_nullable(datcollversion) FROM pg_database "
                                            "WHERE datname=current_database()").stdout.strip()
    a = cl.psql(DB, "SELECT bt_index_parent_check('t_s_uq', true, true)", check=False, tag="p2_amcheck")
    d["amcheck_parent_ok"], d["amcheck_msg"] = a.returncode == 0, m.errline(a.stderr)
    lr = m.lookups_and_ranges(cl, DB, rows)
    d.update({"missed_lookups": lr["seq_point_hits"] - lr["index_point_hits"], "lookups": lr["lookups"],
              "range_mismatches": lr["range_count_mismatches"], "nonempty_ranges": lr["nonempty_ranges"]})
    dup = cl.psql_file(DB, "INSERT INTO t(id,s) SELECT id+10000000, s FROM t ON CONFLICT DO NOTHING; "
                       "SET enable_indexscan=off; SET enable_indexonlyscan=off; SET enable_bitmapscan=off; "
                       "SELECT 'dups', count(*) FROM (SELECT s FROM t GROUP BY s HAVING count(*)>1) x;", "dup_insert")
    ins = [l for l in dup.stdout.splitlines() if l.startswith("INSERT 0 ")]
    dl = [l for l in dup.stdout.splitlines() if l.startswith("dups|")]
    d["reinserted_accepted"] = int(ins[0].split()[2]) if ins else None
    d["duplicate_keys"] = int(dl[0].split("|")[1]) if dl else None
    cl.stop()
    return d


def main():
    rows = order.mixed_strings()
    datafile = m.RAW / "dataset.csv"
    with open(datafile, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        for i, s in enumerate(rows):
            w.writerow([i, s])
    res = {"meta": {"rows": len(rows), "dataset_sha256": hashlib.sha256(datafile.read_bytes()).hexdigest(),
                    "postgres": m.sh([str(m.PG / "postgres"), "--version"]).stdout.strip(),
                    "host_glibc": m.sh(["ldd", "--version"]).stdout.splitlines()[0]}}
    val = {}
    for rel, root in (("focal", order.ROOTS["20.04"]), ("jammy", order.ROOTS["22.04"])):
        val[f"{rel}_host_equals_distro_sort"] = host_sorted(rows, rel) == order.distro_sorted(root, rows)
    val["focal_vs_jammy_adjacent_inverted"] = order.compare(host_sorted(rows, "focal"), host_sorted(rows, "jammy"))
    res["validation"] = val
    print("validation", json.dumps(val), flush=True)
    for name, port, rel2 in (("r5_cutf8_drift", 55452, "jammy"), ("r5_cutf8_stable", 55453, "focal")):
        cl = m.Cluster(name, port)
        phase1(cl, datafile)
        res[name] = phase2(cl, rel2, rows)
        print(name, json.dumps(res[name]), flush=True)
    (OUTDIR / "r5_cutf8_pg.json").write_text(json.dumps(res, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
