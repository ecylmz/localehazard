"""RQ2: collation-data drift and Turkic case mapping in a real PostgreSQL 18.6 server.

Design (protocol/AMENDMENT_A2.md):
  cluster DRIFT : phase 1 runs with glibc 2.27 locale data (LOCPATH=loc/old, libc version shim 2.27);
                  phase 2 restarts the same data directory with glibc 2.43 locale data (LOCPATH=loc/new).
  cluster STABLE: identical, but phase 2 keeps LOCPATH=loc/old (negative control for restart effects).
  In each cluster three databases share one dataset: libc en_US.UTF-8, ICU 'en', and C collation.
All raw psql output is written under results/raw/.
"""
import json, os, random, shutil, subprocess, sys, time, pathlib, hashlib

HERE = pathlib.Path(__file__).resolve().parent
PG = HERE / "pg" / "bin"
OUT = HERE / "results"; RAW = OUT / ("raw_" + (sys.argv[1] if len(sys.argv) > 1 else "synthetic"))
RAW.mkdir(parents=True, exist_ok=True)
SEED = 20261001
N_ROWS = 200_000
N_LOOKUPS = 20_000
N_RANGES = 2_000


DATASET = sys.argv[1] if len(sys.argv) > 1 else "synthetic"


def dataset():
    if DATASET == "dictionary":
        words = sorted({w.strip() for w in open("/usr/share/dict/american-english", encoding="utf-8") if w.strip()})
        rng = random.Random(SEED); rng.shuffle(words)
        return words
    rng = random.Random(SEED)
    vocab = ["co", "op", "re", "data", "base", "file", "index", "van", "der", "berg", "de", "la",
             "mac", "donald", "e", "mail", "pre", "fix", "a", "b", "x", "y", "z", "ab", "cd", "ip",
             "sku", "item", "user", "name", "ali", "ışık", "çağ", "öz", "şen", "ünal", "istanbul", "İzmir"]
    seps = ["", " ", "-", "_", ".", "/", "'"]
    rows = set()
    while len(rows) < N_ROWS:
        k = rng.choice([1, 2, 2, 3, 3, 4])
        parts = []
        for _ in range(k):
            t = rng.choice(vocab) if rng.random() < 0.7 else str(rng.randint(0, 9999))
            if rng.random() < 0.15:
                t = t.capitalize()
            if rng.random() < 0.05:
                t = t.upper()
            parts.append(t)
        s = parts[0]
        for p in parts[1:]:
            s += rng.choice(seps) + p
        rows.add(s)
    rows = sorted(rows)  # bytewise, deterministic
    rng.shuffle(rows)
    return rows


def errline(stderr):
    errs = [l for l in stderr.splitlines() if l.startswith("ERROR")]
    return " | ".join(errs) if errs else ""


def sh(cmd, env=None, check=True, inp=None):
    r = subprocess.run(cmd, env=env, capture_output=True, text=True, input=inp)
    if check and r.returncode != 0:
        raise RuntimeError(f"{cmd}\n{r.stdout}\n{r.stderr}")
    return r


def env_for(locpath, shim):
    e = {"PATH": f"{PG}:/usr/bin:/bin", "LOCPATH": str(HERE / "loc" / locpath), "LC_ALL": "C.UTF-8",
         "PGHOST": "/tmp", "LANG": "C.UTF-8", "PGUSER": "postgres"}
    if shim:
        e["LD_PRELOAD"] = str(HERE / "libcver_shim.so")
        e["SHIM_LIBC_VERSION"] = shim if isinstance(shim, str) else "2.27"
    return e


class Cluster:
    def __init__(self, name, port):
        self.name, self.port = name, port
        self.dir = HERE / "clusters" / name

    def start(self, locpath, shim):
        self.env = env_for(locpath, shim)
        sh([str(PG / "pg_ctl"), "-D", str(self.dir), "-l", str(RAW / f"{self.name}_server.log"), "-w",
            "-o", f"-p {self.port} -k /tmp -c listen_addresses=''", "start"], env=self.env)

    def stop(self):
        sh([str(PG / "pg_ctl"), "-D", str(self.dir), "-w", "-m", "fast", "stop"], env=self.env)

    def psql(self, db, sql, check=True, tag=None):
        r = sh([str(PG / "psql"), "-X", "-p", str(self.port), "-d", db, "-At", "-v", "ON_ERROR_STOP=1",
                "-c", sql], env=self.env, check=check)
        if tag:
            (RAW / f"{self.name}_{db}_{tag}.txt").write_text(r.stdout + "\n--stderr--\n" + r.stderr)
        return r

    def psql_file(self, db, sql, tag):
        r = sh([str(PG / "psql"), "-X", "-p", str(self.port), "-d", db, "-At", "-v", "ON_ERROR_STOP=0"],
               env=self.env, check=False, inp=sql)
        (RAW / f"{self.name}_{db}_{tag}.txt").write_text(r.stdout + "\n--stderr--\n" + r.stderr)
        return r


DBS = {
    "libc_en": "CREATE DATABASE libc_en TEMPLATE template0 LOCALE_PROVIDER libc LOCALE 'en_US.UTF-8' ENCODING 'UTF8'",
    "icu_en": "CREATE DATABASE icu_en TEMPLATE template0 LOCALE_PROVIDER icu ICU_LOCALE 'en' LOCALE 'en_US.UTF-8' ENCODING 'UTF8'",
    "c_coll": "CREATE DATABASE c_coll TEMPLATE template0 LOCALE_PROVIDER libc LOCALE 'C' ENCODING 'UTF8'",
}


def phase1(cl, rows, datafile):
    if cl.dir.exists():
        shutil.rmtree(cl.dir)
    cl.dir.parent.mkdir(exist_ok=True)
    e = env_for("old", True)
    sh([str(PG / "initdb"), "-D", str(cl.dir), "--locale=en_US.UTF-8", "--encoding=UTF8", "-U", "postgres",
        "--no-instructions"], env=e)
    cl.start("old", True)
    for base, ddl0 in DBS.items():
      for db in (base, base + "_rem"):
        ddl = ddl0.replace(f"DATABASE {base} ", f"DATABASE {db} ")
        cl.psql("postgres", ddl)
        cl.psql(db, "CREATE EXTENSION amcheck")
        cl.psql(db, "CREATE TABLE t(id int PRIMARY KEY, s text NOT NULL)")
        sh([str(PG / "psql"), "-X", "-p", str(cl.port), "-d", db, "-v", "ON_ERROR_STOP=1", "-c",
            f"\\copy t(id,s) FROM '{datafile}' WITH (FORMAT csv)"], env=cl.env)
        cl.psql(db, "CREATE UNIQUE INDEX t_s_uq ON t(s)")
        cl.psql(db, "ANALYZE t")
        cl.psql(db, "SELECT datcollversion FROM pg_database WHERE datname=current_database()", tag="p1_collversion")
        # phase-1 sanity: index must verify before drift
        cl.psql(db, "SELECT bt_index_parent_check('t_s_uq', true, true)", tag="p1_amcheck")
    cl.stop()


def lookups_and_ranges(cl, db, rows):
    rng = random.Random(SEED + 1)
    keys = rng.sample(rows, N_LOOKUPS)
    cl.psql(db, "CREATE TABLE IF NOT EXISTS probe(k text)")
    cl.psql(db, "TRUNCATE probe")
    tmp = RAW / f"{cl.name}_{db}_probe.csv"
    import csv
    with open(tmp, "w", newline="") as fh:
        w = csv.writer(fh)
        for k in keys:
            w.writerow([k])
    sh([str(PG / "psql"), "-X", "-p", str(cl.port), "-d", db, "-v", "ON_ERROR_STOP=1", "-c",
        f"\\copy probe(k) FROM '{tmp}' WITH (FORMAT csv)"], env=cl.env)
    # Index-only point lookups via a PL/pgSQL loop with seqscan disabled; seq-scan reference via hash join.
    sql = """
SET enable_seqscan=off; SET enable_bitmapscan=off;
CREATE OR REPLACE FUNCTION idx_hits() RETURNS bigint LANGUAGE plpgsql AS $$
DECLARE r record; n bigint := 0; c bigint; BEGIN
  FOR r IN SELECT k FROM probe LOOP
    SELECT count(*) INTO c FROM t WHERE s = r.k; IF c = 1 THEN n := n + 1; END IF;
  END LOOP; RETURN n; END $$;
SELECT 'index_point_hits', idx_hits();
RESET enable_seqscan; RESET enable_bitmapscan;
SET enable_indexscan=off; SET enable_indexonlyscan=off; SET enable_bitmapscan=off;
SELECT 'seq_point_hits', count(*) FROM probe p WHERE EXISTS (SELECT 1 FROM t WHERE t.s = p.k);
RESET enable_indexscan; RESET enable_indexonlyscan;
SET enable_seqscan=off; SET enable_bitmapscan=off;
CREATE OR REPLACE FUNCTION idx_missed() RETURNS SETOF text LANGUAGE plpgsql AS $$
DECLARE r record; c bigint; BEGIN
  FOR r IN SELECT k FROM probe LOOP
    SELECT count(*) INTO c FROM t WHERE s = r.k; IF c <> 1 THEN RETURN NEXT r.k; END IF;
  END LOOP; END $$;
SELECT 'missed|' || replace(k, E'\n', ' ') FROM idx_missed() AS k;
"""
    r = cl.psql_file(db, sql, "lookups")
    vals = dict(l.split("|") for l in r.stdout.splitlines() if l.count("|") == 1 and not l.startswith("missed|"))
    missed = [l[len("missed|"):] for l in r.stdout.splitlines() if l.startswith("missed|")]
    # Range queries
    pairs = [sorted(rng.sample(rows, 2)) for _ in range(N_RANGES)]
    body = []
    for a, b in pairs:
        a2, b2 = a.replace("'", "''"), b.replace("'", "''")
        body.append(f"SELECT count(*) FROM t WHERE s >= '{a2}' AND s <= '{b2}';")
    idx_sql = "SET enable_seqscan=off; SET enable_bitmapscan=off;\n" + "\n".join(body)
    seq_sql = "SET enable_indexscan=off; SET enable_indexonlyscan=off; SET enable_bitmapscan=off;\n" + "\n".join(body)
    ri = cl.psql_file(db, idx_sql, "ranges_index").stdout.split()
    rs = cl.psql_file(db, seq_sql, "ranges_seq").stdout.split()
    ri = [x for x in ri if x.isdigit()]; rs = [x for x in rs if x.isdigit()]
    mism = sum(1 for x, y in zip(ri, rs) if x != y)
    nonempty = sum(1 for y in rs if y != "0")
    return {"missed_keys": missed, "nonempty_ranges": nonempty, "lookups": N_LOOKUPS, "index_point_hits": int(vals.get("index_point_hits", -1)),
            "seq_point_hits": int(vals.get("seq_point_hits", -1)), "ranges": N_RANGES,
            "range_results_compared": min(len(ri), len(rs)), "range_count_mismatches": mism}


def phase2(cl, locpath, rows, shim_version):
    cl.start(locpath, shim_version)  # shim_version None = host glibc version string is reported
    res = {}
    for db in DBS:
        d = {}
        r = cl.psql(db, "SELECT 1", tag="p2_connect")
        d["connect_warning"] = "collation version mismatch" in r.stderr
        d["recorded_collversion"] = cl.psql(db, "SELECT datcollversion FROM pg_database WHERE datname=current_database()").stdout.strip()
        d["actual_collversion"] = cl.psql(db, "SELECT pg_database_collation_actual_version(oid) FROM pg_database WHERE datname=current_database()").stdout.strip()
        a = cl.psql(db, "SELECT bt_index_check('t_s_uq', true)", check=False, tag="p2_amcheck")
        d["amcheck_bt_index_check_ok"] = a.returncode == 0
        d["amcheck_bt_index_check_msg"] = errline(a.stderr)
        a = cl.psql(db, "SELECT bt_index_parent_check('t_s_uq', true, true)", check=False, tag="p2_amcheck_parent")
        d["amcheck_parent_check_ok"] = a.returncode == 0
        d["amcheck_parent_check_msg"] = errline(a.stderr)
        d.update(lookups_and_ranges(cl, db, rows))
        # PostgreSQL refuses to use a version-mismatched database as a template
        tc = cl.psql("postgres", f"CREATE DATABASE {db}_tmplcopy TEMPLATE {db}", check=False, tag=f"template_copy_{db}")
        d["template_copy_refused"] = tc.returncode != 0
        # Uniqueness: re-insert every existing key; a sound unique index must reject all of them
        dup = cl.psql_file(db, "INSERT INTO t(id,s) SELECT id+10000000, s FROM t ON CONFLICT DO NOTHING; "
                           "SET enable_indexscan=off; SET enable_indexonlyscan=off; SET enable_bitmapscan=off; "
                           "SELECT 'dups', count(*) FROM (SELECT s FROM t GROUP BY s HAVING count(*)>1) x;", "dup_insert")
        ins = [l for l in dup.stdout.splitlines() if l.startswith("INSERT 0 ")]
        d["reinserted_existing_keys_accepted"] = int(ins[0].split()[2]) if ins else None
        line = [l for l in dup.stdout.splitlines() if l.startswith("dups|")]
        d["duplicate_keys_admitted"] = int(line[0].split("|")[1]) if line else None
        rx = cl.psql(db, "REINDEX INDEX t_s_uq", check=False, tag="reindex_after_dups")
        d["reindex_after_dups_ok"] = rx.returncode == 0
        d["reindex_after_dups_msg"] = errline(rx.stderr) + " " + " ".join(l for l in rx.stderr.splitlines() if l.startswith("DETAIL"))
        # Remediation on the clone: REINDEX then refresh the recorded version, then verify
        clone = f"{db}_rem"
        rx = cl.psql(clone, "REINDEX DATABASE " + clone, check=False, tag="reindex_clone")
        cl.psql(clone, f"ALTER DATABASE {clone} REFRESH COLLATION VERSION", check=False, tag="refresh_clone")
        a = cl.psql(clone, "SELECT bt_index_parent_check('t_s_uq', true, true)", check=False, tag="amcheck_clone")
        d["remediated_clone_amcheck_ok"] = a.returncode == 0 and rx.returncode == 0
        cm = lookups_and_ranges(cl, clone, rows)
        d["remediated_clone_missed"] = cm["seq_point_hits"] - cm["index_point_hits"]
        d["remediated_clone_range_mismatches"] = cm["range_count_mismatches"]
        res[db] = d
    cl.stop()
    return res


TURKIC_SQL = r"""
CREATE EXTENSION IF NOT EXISTS citext;
SELECT 'lower_FILE', lower('FILE');
SELECT 'upper_file', upper('file');
SELECT 'ilike', ('FILE' ILIKE 'file')::text;
SELECT 'citext_eq', ('TITLE'::citext = 'title'::citext)::text;
SELECT 'lower_eq', (lower('ADMIN@EXAMPLE.ORG') = lower('admin@example.org'))::text;
CREATE TABLE acct(email text);
CREATE UNIQUE INDEX acct_lower_uq ON acct(lower(email));
INSERT INTO acct VALUES ('admin@example.org');
INSERT INTO acct VALUES ('ADMIN@EXAMPLE.ORG');
SELECT 'accounts_admitted', count(*) FROM acct;
CREATE TABLE citext_acct(email citext UNIQUE);
INSERT INTO citext_acct VALUES ('info@example.org');
INSERT INTO citext_acct VALUES ('INFO@EXAMPLE.ORG');
SELECT 'citext_accounts_admitted', count(*) FROM citext_acct;
CREATE TABLE FILE_INDEX(id int);
SELECT 'unquoted_identifier', relname FROM pg_class WHERE relname ILIKE 'f%le_index';
"""

TURKIC_DBS = {
    "tr_libc": "CREATE DATABASE tr_libc TEMPLATE template0 LOCALE_PROVIDER libc LOCALE 'tr_TR.UTF-8' ENCODING 'UTF8'",
    "tr_icu": "CREATE DATABASE tr_icu TEMPLATE template0 LOCALE_PROVIDER icu ICU_LOCALE 'tr' LOCALE 'tr_TR.UTF-8' ENCODING 'UTF8'",
    "en_libc": "CREATE DATABASE en_libc TEMPLATE template0 LOCALE_PROVIDER libc LOCALE 'en_US.UTF-8' ENCODING 'UTF8'",
    "tr_coll_c_ctype": "CREATE DATABASE tr_coll_c_ctype TEMPLATE template0 LOCALE_PROVIDER libc LC_COLLATE 'C' LC_CTYPE 'tr_TR.UTF-8' ENCODING 'UTF8'",
    "builtin_c": "CREATE DATABASE builtin_c TEMPLATE template0 LOCALE_PROVIDER builtin BUILTIN_LOCALE 'C.UTF-8' LOCALE 'C.UTF-8' ENCODING 'UTF8'",
}


def turkic():
    cl = Cluster("turkic", 55439)
    if cl.dir.exists():
        shutil.rmtree(cl.dir)
    e = env_for("new", False)
    sh([str(PG / "initdb"), "-D", str(cl.dir), "--locale=en_US.UTF-8", "--encoding=UTF8", "-U", "postgres",
        "--no-instructions"], env=e)
    cl.start("new", False)
    res = {}
    for db, ddl in TURKIC_DBS.items():
        cl.psql("postgres", ddl, check=False, tag=f"create_{db}")
        r = cl.psql_file(db, TURKIC_SQL, "turkic")
        vals = {}
        for l in r.stdout.splitlines():
            if "|" in l:
                k, v = l.split("|", 1); vals[k] = v
        vals["errors"] = [l for l in r.stderr.splitlines() if l.startswith("ERROR")]
        res[db] = vals
    cl.stop()
    return res


def main():
    rows = dataset()
    datafile = RAW / "dataset.csv"
    import csv
    with open(datafile, "w", newline="") as fh:
        w = csv.writer(fh)
        for i, s in enumerate(rows):
            w.writerow([i, s])
    meta = {"seed": SEED, "rows": len(rows), "dataset": DATASET, "dataset_sha256": hashlib.sha256(datafile.read_bytes()).hexdigest(),
            "postgres": sh([str(PG / "postgres"), "--version"]).stdout.strip(),
            "host_glibc": sh(["ldd", "--version"]).stdout.splitlines()[0],
            "old_locale_source": "glibc-2.27/localedata (sha256 of tarball 5172de54...fc72)"}
    results = {"meta": meta}
    for name, port, p2, shimv in [("drift", 55437, "new", None), ("drift228", 55440, "v228", "2.28"),
                                  ("silent", 55441, "new", "2.27"), ("stable", 55438, "old", "2.27")]:
        cl = Cluster(name, port)
        phase1(cl, rows, datafile)
        results[name] = phase2(cl, p2, rows, shimv)
        results[name]["_condition"] = {"phase2_locale_data": p2, "reported_glibc_version": shimv or "host (2.43)"}
        print(name, json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "missed_keys"} if isinstance(v, dict) else v for k, v in results[name].items()}, indent=1), flush=True)
    if DATASET == "synthetic":
        results["turkic"] = turkic()
    print(json.dumps(results.get("turkic"), indent=1, ensure_ascii=False))
    (OUT / f"dbms_results_{DATASET}.json").write_text(json.dumps(results, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
