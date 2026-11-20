"""Round 5 (short PostgreSQL paper): real operating-system upgrades under existing PostgreSQL indexes.

Post hoc (protocol/DEVIATIONS.md, 2026-11-16). PostgreSQL 18.6 is built from the same tarball in Docker images of
Ubuntu 18.04 (glibc 2.27), 20.04 (glibc 2.31) and 22.04 (glibc 2.35), each with its own glibc and locale data
(en_US.UTF-8 compiled by that release's localedef, C.UTF-8 as shipped). A cluster is created and loaded in one
image, stopped, and started on the same data directory in the next image. No emulation and no version shim.
Paths: 18.04 -> 20.04 (contains the glibc 2.28 collation update), 20.04 -> 22.04 (Debian's C.UTF-8 replaced by
glibc's), and 20.04 -> 20.04 (restart control). Databases: libc en_US.UTF-8 with the synthetic and the dictionary
keys, libc C.UTF-8 with the synthetic keys and with the mixed-plane strings, and C collation with the synthetic keys.
Checks after the restart, as in run_dbms_experiment.py: version warning, amcheck, 20,000 point lookups (or all keys
when there are fewer), 2,000 range counts, and re-insertion of every existing key.
Clients run on the host (psql 18.6) and connect over TCP to the server in the container.
Usage: python3 dbms/r5_real_upgrade.py OUTDIR
"""
import csv, hashlib, json, pathlib, subprocess, sys, time

OUTDIR = pathlib.Path(sys.argv[1]).resolve()
sys.argv = [sys.argv[0], "synthetic"]
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_dbms_experiment as m  # noqa: E402
import r5_cutf8_order as order  # noqa: E402

OUTDIR.mkdir(parents=True, exist_ok=True)
m.RAW = OUTDIR / "raw_real_upgrade"
m.RAW.mkdir(exist_ok=True)
IMAGES = {"18.04": "lh-pg186:18.04", "20.04": "lh-pg186:20.04", "22.04": "lh-pg186:22.04"}
PATHS = [("bionic_to_focal", "18.04", "20.04", 55461), ("focal_to_jammy", "20.04", "22.04", 55462),
         ("focal_restart", "20.04", "20.04", 55463)]
DATABASES = {  # name -> (locale clause, dataset)
    "en_syn": ("LOCALE_PROVIDER libc LOCALE 'en_US.UTF-8'", "synthetic"),
    "en_dic": ("LOCALE_PROVIDER libc LOCALE 'en_US.UTF-8'", "dictionary"),
    "cutf8_syn": ("LOCALE_PROVIDER libc LOCALE 'C.UTF-8'", "synthetic"),
    "cutf8_mixed": ("LOCALE_PROVIDER libc LOCALE 'C.UTF-8'", "mixed"),
    "c_syn": ("LOCALE_PROVIDER libc LOCALE 'C'", "synthetic"),
}


def docker(*args, check=True):
    return m.sh(["sudo", "-n", "docker", *args], check=check)


class DockerCluster(m.Cluster):
    def __init__(self, name, port):
        super().__init__(name, port)
        self.dir = m.HERE / "clusters" / name  # data directories stay out of results/
        self.env = {"PATH": f"{m.PG}:/usr/bin:/bin", "PGHOST": "127.0.0.1", "PGPORT": str(port), "PGUSER": "postgres",
                    "LD_LIBRARY_PATH": str(m.HERE / "pg" / "lib"), "LC_ALL": "C.UTF-8"}
        self.container = f"lh_{name}"

    def run_in(self, image, *cmd):
        return docker("run", "--rm", "-v", f"{self.dir}:/data", image, *cmd)

    def start(self, image):
        docker("rm", "-f", self.container, check=False)
        docker("run", "-d", "--name", self.container, "--network", "host", "-v", f"{self.dir}:/data", image,
               "/opt/pg/bin/postgres", "-D", "/data/pgdata", "-p", str(self.port), "-c", "listen_addresses=127.0.0.1",
               "-k", "/tmp")
        for _ in range(120):
            if m.sh([str(m.PG / "pg_isready"), "-h", "127.0.0.1", "-p", str(self.port)], env=self.env,
                    check=False).returncode == 0:
                return
            time.sleep(1)
        raise RuntimeError(docker("logs", self.container, check=False).stderr)

    def stop(self):
        docker("exec", self.container, "/opt/pg/bin/pg_ctl", "-D", "/data/pgdata", "-w", "-m", "fast", "stop", check=False)
        logs = docker("logs", self.container, check=False)
        (m.RAW / f"{self.name}_server_{int(time.time())}.log").write_text(logs.stdout + logs.stderr)
        docker("rm", "-f", self.container, check=False)


def environment(image):
    r = docker("run", "--rm", image, "sh", "-c", "ldd --version | head -1; ls /usr/lib/locale; locale -a")
    return r.stdout.strip().splitlines()


def load(cl, image, data):
    m.sh(["sudo", "-n", "rm", "-rf", str(cl.dir)], check=False)
    cl.dir.mkdir(parents=True)
    m.sh(["sudo", "-n", "chown", "4242:4242", str(cl.dir)])
    cl.run_in(image, "/opt/pg/bin/initdb", "-D", "/data/pgdata", "--locale=C.UTF-8", "--encoding=UTF8", "-U",
              "postgres", "--no-instructions")
    cl.start(image)
    for db, (clause, ds) in DATABASES.items():
        cl.psql("postgres", f"CREATE DATABASE {db} TEMPLATE template0 {clause} ENCODING 'UTF8'")
        cl.psql(db, "CREATE EXTENSION amcheck")
        cl.psql(db, "CREATE TABLE t(id int PRIMARY KEY, s text NOT NULL)")
        m.sh([str(m.PG / "psql"), "-X", "-d", db, "-v", "ON_ERROR_STOP=1", "-c",
              f"\\copy t(id,s) FROM '{data[ds]['file']}' WITH (FORMAT csv)"], env=cl.env)
        cl.psql(db, "CREATE UNIQUE INDEX t_s_uq ON t(s)")
        cl.psql(db, "ANALYZE t")
        cl.psql(db, "SELECT bt_index_parent_check('t_s_uq', true, true)", tag=f"{db}_p1_amcheck")
        cl.psql(db, "SELECT quote_nullable(datcollversion) FROM pg_database WHERE datname=current_database()",
                tag=f"{db}_p1_collversion")
    cl.stop()


def check(cl, db, rows):
    d = {}
    r = cl.psql(db, "SELECT 1", tag=f"{db}_p2_connect")
    d["connect_warning"] = "collation version mismatch" in r.stderr
    d["recorded_collversion"] = cl.psql(db, "SELECT quote_nullable(datcollversion) FROM pg_database "
                                            "WHERE datname=current_database()").stdout.strip()
    d["actual_collversion"] = cl.psql(db, "SELECT quote_nullable(pg_database_collation_actual_version(oid)) "
                                          "FROM pg_database WHERE datname=current_database()").stdout.strip()
    a = cl.psql(db, "SELECT bt_index_parent_check('t_s_uq', true, true)", check=False, tag=f"{db}_p2_amcheck")
    d["amcheck_parent_ok"], d["amcheck_msg"] = a.returncode == 0, m.errline(a.stderr)
    m.N_LOOKUPS = min(20_000, len(rows))
    lr = m.lookups_and_ranges(cl, db, rows)
    d.update({"missed_lookups": lr["seq_point_hits"] - lr["index_point_hits"], "lookups": lr["lookups"],
              "range_mismatches": lr["range_count_mismatches"], "nonempty_ranges": lr["nonempty_ranges"]})
    dup = cl.psql_file(db, "INSERT INTO t(id,s) SELECT id+10000000, s FROM t ON CONFLICT DO NOTHING; "
                       "SET enable_indexscan=off; SET enable_indexonlyscan=off; SET enable_bitmapscan=off; "
                       "SELECT 'dups', count(*) FROM (SELECT s FROM t GROUP BY s HAVING count(*)>1) x;", f"{db}_dup")
    ins = [l for l in dup.stdout.splitlines() if l.startswith("INSERT 0 ")]
    dl = [l for l in dup.stdout.splitlines() if l.startswith("dups|")]
    d["reinserted_accepted"] = int(ins[0].split()[2]) if ins else None
    d["duplicate_keys"] = int(dl[0].split("|")[1]) if dl else None
    return d


def main():
    data = {}
    for ds in ("synthetic", "dictionary"):
        f = m.HERE / f"results/raw_{ds}/dataset.csv"
        data[ds] = {"file": f, "rows": [r[1] for r in csv.reader(open(f, encoding="utf-8"))]}
    mixed = order.mixed_strings()
    f = m.RAW / "mixed.csv"
    with open(f, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        for i, s in enumerate(mixed):
            w.writerow([i, s])
    data["mixed"] = {"file": f, "rows": mixed}
    res = {"meta": {"images": {rel: environment(img) for rel, img in IMAGES.items()},
                    "datasets": {k: {"rows": len(v["rows"]), "sha256": hashlib.sha256(v["file"].read_bytes()).hexdigest()}
                                 for k, v in data.items()}}}
    print(json.dumps(res["meta"]), flush=True)
    for name, rel1, rel2, port in PATHS:
        cl = DockerCluster(name, port)
        load(cl, IMAGES[rel1], data)
        cl.start(IMAGES[rel2])
        res[name] = {db: check(cl, db, data[ds]["rows"]) for db, (_, ds) in DATABASES.items()}
        cl.stop()
        res[name]["_path"] = {"load": rel1, "restart": rel2}
        print(name, json.dumps(res[name]), flush=True)
        (OUTDIR / "r5_real_upgrade.json").write_text(json.dumps(res, indent=1, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
