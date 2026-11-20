"""Round 5 (short PostgreSQL paper): repair paths after a glibc collation-data change.

Post hoc extension of the drift condition of run_dbms_experiment.py (protocol/DEVIATIONS.md, 2026-11-15).
One cluster is loaded and indexed under glibc 2.27 locale data (reported version 2.27) and restarted under the
host 2.43 data (reported version 2.43), as in the drift condition. Three copies of the libc en_US.UTF-8 database
take three paths after the restart:
  clean   : REINDEX DATABASE, then ALTER DATABASE ... REFRESH COLLATION VERSION, before any write;
  refresh : REFRESH COLLATION VERSION only (no reindex), the step that silences the warning;
  dirty   : every existing key is re-inserted first (duplicates enter), then REINDEX (expected to fail),
            removal of the later copy of each duplicate key found by a sequential scan, REINDEX, REFRESH.
After each path the script runs amcheck, the 20,000 point lookups and 2,000 range counts of the original
experiment, and the re-insertion of every existing key, which a sound unique index must reject entirely.
Usage: python3 dbms/r5_repair.py synthetic|dictionary OUTDIR
"""
import json, pathlib, sys

DATASET, OUTDIR = sys.argv[1], pathlib.Path(sys.argv[2]).resolve()
sys.argv = [sys.argv[0], DATASET]  # the original driver reads the dataset name from argv[1]
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import run_dbms_experiment as m  # noqa: E402

_env_for = m.env_for
def _env_with_libs(locpath, shim):  # the build's RUNPATH points to an earlier checkout path
    e = _env_for(locpath, shim)
    e["LD_LIBRARY_PATH"] = str(m.HERE / "pg" / "lib")
    return e
m.env_for = _env_with_libs

OUTDIR.mkdir(parents=True, exist_ok=True)
m.RAW = OUTDIR / f"raw_{DATASET}"
m.RAW.mkdir(exist_ok=True)
m.DBS = {"libc_en": m.DBS["libc_en"]}
PATHS = ("clean", "refresh", "dirty")

REINSERT = ("INSERT INTO t(id,s) SELECT id+{off}, s FROM t WHERE id < 10000000 ON CONFLICT DO NOTHING; "
            "SET enable_indexscan=off; SET enable_indexonlyscan=off; SET enable_bitmapscan=off; "
            "SELECT 'dups', count(*) FROM (SELECT s FROM t GROUP BY s HAVING count(*)>1) x;")
DEDUP = ("SET enable_indexscan=off; SET enable_indexonlyscan=off; SET enable_bitmapscan=off; "
         "DELETE FROM t a USING t b WHERE a.s = b.s AND a.id > b.id; "
         "SELECT 'remaining_dups', count(*) FROM (SELECT s FROM t GROUP BY s HAVING count(*)>1) x;")


def reinsert(cl, db, off, tag):
    r = cl.psql_file(db, REINSERT.format(off=off), tag)
    ins = [l for l in r.stdout.splitlines() if l.startswith("INSERT 0 ")]
    dup = [l for l in r.stdout.splitlines() if l.startswith("dups|")]
    return {"accepted": int(ins[0].split()[2]) if ins else None,
            "duplicate_keys": int(dup[0].split("|")[1]) if dup else None, "error": m.errline(r.stderr)}


def checks(cl, db, rows, tag):
    a = cl.psql(db, "SELECT bt_index_parent_check('t_s_uq', true, true)", check=False, tag=f"{tag}_amcheck")
    lr = m.lookups_and_ranges(cl, db, rows)
    warn = cl.psql(db, "SELECT 1", tag=f"{tag}_connect")
    return {"amcheck_parent_ok": a.returncode == 0, "amcheck_msg": m.errline(a.stderr),
            "connect_warning": "collation version mismatch" in warn.stderr,
            "missed_lookups": lr["seq_point_hits"] - lr["index_point_hits"], "lookups": lr["lookups"],
            "range_mismatches": lr["range_count_mismatches"], "nonempty_ranges": lr["nonempty_ranges"]}


def main():
    rows = m.dataset()
    datafile = m.RAW / "dataset.csv"
    import csv, hashlib
    with open(datafile, "w", newline="") as fh:
        w = csv.writer(fh)
        for i, s in enumerate(rows):
            w.writerow([i, s])
    cl = m.Cluster("r5_repair", 55450)
    # phase 1 creates libc_en and libc_en_rem; add the two further copies the same way
    base = m.DBS["libc_en"]
    m.DBS = {f"libc_en_{p}": base.replace("DATABASE libc_en ", f"DATABASE libc_en_{p} ") for p in PATHS}
    m.phase1(cl, rows, datafile)  # also creates *_rem copies, unused here
    cl.start("new", None)  # host 2.43 data, host version string reported
    res = {"meta": {"dataset": DATASET, "rows": len(rows),
                    "dataset_sha256": hashlib.sha256(datafile.read_bytes()).hexdigest(),
                    "postgres": m.sh([str(m.PG / "postgres"), "--version"]).stdout.strip()}}
    for p in PATHS:
        db, d = f"libc_en_{p}", {}
        d["before"] = checks(cl, db, rows, f"{p}_before")
        if p == "clean":
            rx = cl.psql(db, f"REINDEX DATABASE {db}", check=False, tag="clean_reindex")
            d["reindex_ok"] = rx.returncode == 0
            cl.psql(db, f"ALTER DATABASE {db} REFRESH COLLATION VERSION", tag="clean_refresh")
        elif p == "refresh":
            cl.psql(db, f"ALTER DATABASE {db} REFRESH COLLATION VERSION", tag="refresh_refresh")
        else:
            d["first_reinsert"] = reinsert(cl, db, 10000000, "dirty_reinsert1")
            rx = cl.psql(db, "REINDEX INDEX t_s_uq", check=False, tag="dirty_reindex1")
            d["reindex_with_dups_ok"] = rx.returncode == 0
            d["reindex_with_dups_msg"] = m.errline(rx.stderr)
            r = cl.psql_file(db, DEDUP, "dirty_dedup")
            dl = [l for l in r.stdout.splitlines() if l.startswith("DELETE ")]
            rem = [l for l in r.stdout.splitlines() if l.startswith("remaining_dups|")]
            d["dedup_deleted_rows"] = int(dl[0].split()[1]) if dl else None
            d["dedup_remaining_dups"] = int(rem[0].split("|")[1]) if rem else None
            rx = cl.psql(db, "REINDEX INDEX t_s_uq", check=False, tag="dirty_reindex2")
            d["reindex_after_dedup_ok"] = rx.returncode == 0
            cl.psql(db, f"ALTER DATABASE {db} REFRESH COLLATION VERSION", tag="dirty_refresh")
        d["after"] = checks(cl, db, rows, f"{p}_after")
        d["after_reinsert"] = reinsert(cl, db, 20000000, f"{p}_reinsert_after")
        res[p] = d
        print(p, json.dumps(d), flush=True)
    cl.stop()
    (OUTDIR / f"r5_repair_{DATASET}.json").write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
