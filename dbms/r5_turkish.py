"""Round 5 (short PostgreSQL paper): Turkish case mapping and case-insensitive uniqueness, extended matrix.

Post hoc extension of turkic() in run_dbms_experiment.py (protocol/DEVIATIONS.md, 2026-11-15).
The application rule under test is ASCII case-insensitive equality of keys such as e-mail addresses:
admin@example.org and ADMIN@EXAMPLE.ORG are the same key. Two further pairs, ışık / IŞIK and istanbul / İSTANBUL, are Turkish word pairs
whose equality a Turkish linguistic rule needs; they show the cost of each configuration for linguistic text.
Each uniqueness mechanism is a table with one unique constraint. The script inserts the lowercase key and then
the uppercase key and records whether the second insert was accepted (a duplicate under the application rule).
Usage: python3 dbms/r5_turkish.py OUTDIR
"""
import json, pathlib, shutil, sys

OUTDIR = pathlib.Path(sys.argv[1]).resolve()
sys.argv = [sys.argv[0], "synthetic"]
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import run_dbms_experiment as m  # noqa: E402

_env_for = m.env_for
def _env_with_libs(locpath, shim):  # the build's RUNPATH points to an earlier checkout path
    e = _env_for(locpath, shim)
    e["LD_LIBRARY_PATH"] = str(m.HERE / "pg" / "lib")
    return e
m.env_for = _env_with_libs

OUTDIR.mkdir(parents=True, exist_ok=True)
m.RAW = OUTDIR / "raw_turkish"
m.RAW.mkdir(exist_ok=True)

DATABASES = {
    "tr_libc": "LOCALE_PROVIDER libc LOCALE 'tr_TR.UTF-8'",
    "tr_icu": "LOCALE_PROVIDER icu ICU_LOCALE 'tr' LOCALE 'tr_TR.UTF-8'",
    "tr_coll_c_ctype": "LOCALE_PROVIDER libc LC_COLLATE 'C' LC_CTYPE 'tr_TR.UTF-8'",
    "en_libc": "LOCALE_PROVIDER libc LOCALE 'en_US.UTF-8'",
    "builtin_c": "LOCALE_PROVIDER builtin BUILTIN_LOCALE 'C.UTF-8' LOCALE 'C.UTF-8'",
    "builtin_unicode_fast": "LOCALE_PROVIDER builtin BUILTIN_LOCALE 'PG_UNICODE_FAST' LOCALE 'C.UTF-8'",
}

# name -> (DDL for table k, description). Every table has one text column v and one unique constraint.
MECHANISMS = {
    "lower_index": ("CREATE TABLE k(v text); CREATE UNIQUE INDEX ON k(lower(v))",
                    "unique index on lower(v), database collation"),
    "upper_index": ("CREATE TABLE k(v text); CREATE UNIQUE INDEX ON k(upper(v))",
                    "unique index on upper(v), database collation"),
    "casefold_index": ("CREATE TABLE k(v text); CREATE UNIQUE INDEX ON k(casefold(v))",
                       "unique index on casefold(v) (PostgreSQL 18), database collation"),
    "citext_unique": ("CREATE TABLE k(v citext UNIQUE)", "UNIQUE citext column, database collation"),
    "lower_arg_c": ("CREATE TABLE k(v text); CREATE UNIQUE INDEX ON k(lower(v COLLATE \"C\"))",
                    "unique index on lower(v COLLATE \"C\"): case mapping under C"),
    "lower_result_c": ("CREATE TABLE k(v text); CREATE UNIQUE INDEX ON k((lower(v) COLLATE \"C\"))",
                       "unique index on lower(v) COLLATE \"C\": mapping under the database ctype, C order"),
    "column_c_lower": ("CREATE TABLE k(v text COLLATE \"C\"); CREATE UNIQUE INDEX ON k(lower(v))",
                       "column declared COLLATE \"C\", unique index on lower(v)"),
    "citext_column_c": ("CREATE TABLE k(v citext COLLATE \"C\" UNIQUE)", "UNIQUE citext column declared COLLATE \"C\""),
    "icu_und_ci": ("CREATE COLLATION ci_und (provider = icu, locale = 'und-u-ks-level2', deterministic = false); "
                   "CREATE TABLE k(v text COLLATE ci_und UNIQUE)",
                   "UNIQUE column with nondeterministic ICU collation und-u-ks-level2"),
    "icu_tr_ci": ("CREATE COLLATION ci_tr (provider = icu, locale = 'tr-u-ks-level2', deterministic = false); "
                  "CREATE TABLE k(v text COLLATE ci_tr UNIQUE)",
                  "UNIQUE column with nondeterministic ICU collation tr-u-ks-level2"),
}
PAIRS = {"ascii_email": ("admin@example.org", "ADMIN@EXAMPLE.ORG"), "turkish_dotless": ("ışık", "IŞIK"),
         "turkish_dotted": ("istanbul", "İSTANBUL")}


def run_mechanism(cl, db, mech, ddl, pair):
    lo, up = PAIRS[pair]
    sql = (f"DROP TABLE IF EXISTS k; DROP COLLATION IF EXISTS ci_und; DROP COLLATION IF EXISTS ci_tr;\n{ddl};\n"
           f"INSERT INTO k VALUES ('{lo}');\nINSERT INTO k VALUES ('{up}');\nSELECT 'rows', count(*) FROM k;\n")
    r = cl.psql_file(db, sql, f"{mech}_{pair}")
    rows = [l for l in r.stdout.splitlines() if l.startswith("rows|")]
    errs = [l for l in r.stderr.splitlines() if l.startswith("ERROR")]
    setup_error = any("unique" not in e and "duplicate" not in e for e in errs)
    n = int(rows[0].split("|")[1]) if rows else None
    return {"rows": n, "second_accepted": None if setup_error or n is None else n == 2, "errors": errs}


def main():
    cl = m.Cluster("r5_turkish", 55451)
    if cl.dir.exists():
        shutil.rmtree(cl.dir)
    cl.dir.parent.mkdir(exist_ok=True)
    e = m.env_for("new", False)
    m.sh([str(m.PG / "initdb"), "-D", str(cl.dir), "--locale=en_US.UTF-8", "--encoding=UTF8", "-U", "postgres",
          "--no-instructions"], env=e)
    cl.start("new", False)
    res = {"meta": {"postgres": m.sh([str(m.PG / "postgres"), "--version"]).stdout.strip(),
                    "icu": cl.psql("postgres", "SELECT icu_unicode_version()", check=False).stdout.strip(),
                    "pairs": PAIRS, "mechanisms": {k: v[1] for k, v in MECHANISMS.items()}}}
    for db, spec in DATABASES.items():
        cl.psql("postgres", f"CREATE DATABASE {db} TEMPLATE template0 {spec} ENCODING 'UTF8'", tag=f"create_{db}")
        cl.psql(db, "CREATE EXTENSION citext")
        d = {"lower_FILE": cl.psql(db, "SELECT lower('FILE')").stdout.strip(),
             "lower_FILE_collate_c": cl.psql(db, "SELECT lower('FILE' COLLATE \"C\")").stdout.strip(),
             "casefold_FILE": cl.psql(db, "SELECT casefold('FILE')", check=False).stdout.strip(),
             "datctype": cl.psql(db, "SELECT datctype || ' / ' || datcollate || ' / ' || datlocprovider::text "
                                     "FROM pg_database WHERE datname = current_database()").stdout.strip()}
        for mech, (ddl, _) in MECHANISMS.items():
            for pair in PAIRS:
                d[f"{mech}|{pair}"] = run_mechanism(cl, db, mech, ddl, pair)
        res[db] = d
        print(db, json.dumps(d, ensure_ascii=False), flush=True)
    cl.stop()
    (OUTDIR / "r5_turkish.json").write_text(json.dumps(res, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
