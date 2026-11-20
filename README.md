# Collation changes and Turkish case mapping in PostgreSQL: replication package

This package belongs to the paper "Collation Changes and Turkish Case Mapping in PostgreSQL: Effects on Index Lookups and Uniqueness". It contains the scripts, the build files, the raw outputs, and the decision log of every experiment in the paper.

The experiments use PostgreSQL 18.6. They measure two things:

- RQ1, collation changes: the glibc collation data under an existing unique B-tree index change. The experiments measure the damage to the index, the warnings of PostgreSQL, and the repairs that restore the index.
- RQ2, Turkish case mapping: which case-insensitive unique keys enforce an ASCII equality rule, such as `admin@example.org` = `ADMIN@EXAMPLE.ORG`, under a Turkish locale.

## Reproducibility level

The package supports derived replay. `make numbers` regenerates every number macro and the two tables of the paper from the deposited results. It needs Python 3 and its standard library only, and it uses no network.

The experiments can also run again from pinned sources (see "Rerun the experiments"). This needs Linux on x86_64, a C toolchain, Docker, and a few gigabytes of disk space.

## Contents

| Path | Contents |
|---|---|
| `dbms/run_dbms_experiment.py` | Emulated drift experiment: glibc 2.27 locale data under an index, then 2.28 or 2.43 data, with a library shim that sets the reported glibc version |
| `dbms/emulation_check.py` | Compares the emulated 2.27 order with a real glibc 2.27 runtime (Ubuntu 18.04) |
| `dbms/libcver_shim.c` | Source of the version shim |
| `dbms/build_env.sh` | Downloads PostgreSQL 18.6, glibc 2.27 and 2.28 sources, and helper tools with SHA-256 checks, and builds them |
| `dbms/r4_collversion_c_utf8.sh` | Shows which collation version PostgreSQL records for libc and builtin C.UTF-8 |
| `dbms/r5_repair.py` | Three repair paths after drift |
| `dbms/r5_turkish.py` | Six database locales, ten unique keys, three case pairs |
| `dbms/r5_cutf8_order.py` | C.UTF-8 sort order of Ubuntu 18.04, 20.04, and 22.04 |
| `dbms/r5_real_upgrade.py`, `dbms/docker/Dockerfile` | Real operating-system upgrades: a cluster made in one Ubuntu release restarts in the next |
| `dbms/r5_cutf8_pg.py` | An attempt to load Ubuntu C.UTF-8 files into the host C library. Its validation failed, and the paper does not use its outputs |
| `dbms/results/` | Raw outputs of the emulated drift experiment and the emulation check |
| `results/r5/` | Recorded runs of the round-5 experiments. Each folder has `run.json` (command, commit, times, status) and `run.log` |
| `results/r4/rq3_collversion_c_utf8-2/` | Recorded run of the version check |
| `src/r4_numbers.py`, `src/r5_numbers.py` | Write the macros and the tables of the paper |
| `numbers/` | Output of `make numbers` |
| `protocol/AMENDMENT_A2.md` | Design of the emulated drift experiment |
| `protocol/DEVIATIONS.md` | Decision log: every change to the design, with the date and the results known at that time |

The commit hashes in `run.json` refer to the private repository of the study.

## Map from the paper to the files

| Paper | Script | Results | Status |
|---|---|---|---|
| Table 1, emulated rows | `dbms/run_dbms_experiment.py` | `dbms/results/dbms_results_*.json`, `dbms/results/raw_*` | Planned (silent and 2.28 conditions added after review) |
| Emulation check | `dbms/emulation_check.py` | `dbms/results/emulation/` | Post hoc |
| Table 1, Ubuntu rows | `dbms/r5_real_upgrade.py` | `results/r5/real_upgrade/` | Post hoc |
| C.UTF-8 order counts | `dbms/r5_cutf8_order.py` | `results/r5/cutf8_order/` | Post hoc |
| Repair paths | `dbms/r5_repair.py` | `results/r5/repair_synthetic/`, `results/r5/repair_dictionary/` | Post hoc |
| No version for libc C.UTF-8 | `dbms/r4_collversion_c_utf8.sh` | `results/r4/rq3_collversion_c_utf8-2/` | Post hoc |
| Table 2, RQ2 | `dbms/r5_turkish.py` | `results/r5/turkish/` | Post hoc |
| All macros and both tables | `src/r4_numbers.py`, `src/r5_numbers.py` | `numbers/` | |

## Rebuild the numbers

```
make numbers
```

The macros go to `numbers/numbers_r4.tex` and `numbers/numbers_r5.tex`, and the tables go to `numbers/tab_drift.tex` and `numbers/tab_turkish.tex`. The tables of the paper use the same values with small layout changes.

## Rerun the experiments

Run the commands from the root of the package as a user that is not root, because PostgreSQL refuses to run as root.

1. Build PostgreSQL 18.6 and the glibc locale data. The `--bionic` option also prepares the real glibc 2.27 runtime of Ubuntu 18.04 in `dbms/bionic`.

   ```
   sh dbms/build_env.sh --bionic
   ```

2. Run the emulated drift experiment and its check.

   ```
   python3 dbms/run_dbms_experiment.py synthetic
   python3 dbms/run_dbms_experiment.py dictionary
   python3 dbms/emulation_check.py
   ```

3. For the C.UTF-8 order, download `ubuntu-base-20.04.5-base-amd64.tar.gz` and `ubuntu-base-22.04.5-base-amd64.tar.gz` from cdimage.ubuntu.com. Make sure that their checksums match the `SHA256SUMS` file of each release. Unpack them into `dbms/rootfs/focal` and `dbms/rootfs/jammy`.

4. For the real upgrades, build one image for each release. The build context is `dbms/`, and it needs `dbms/src/postgresql-18.6.tar.bz2` from step 1.

   ```
   docker build --build-arg BASE=ubuntu:18.04 -t lh-pg186:18.04 dbms
   docker build --build-arg BASE=ubuntu:20.04 -t lh-pg186:20.04 dbms
   docker build --build-arg BASE=ubuntu:22.04 -t lh-pg186:22.04 dbms
   ```

   The recorded runs used these base images:

   | Tag | Digest |
   |---|---|
   | `ubuntu:18.04` | `sha256:152dc042452c496007f07ca9127571cb9c29697f42acbfad72324b2bb2e43c98` |
   | `ubuntu:20.04` | `sha256:8feb4d8ca5354def3d8fce243717141ce31e2c428701f6682bd2fafe15388214` |
   | `ubuntu:22.04` | `sha256:9abcaffc92a5279fff3a6a41635c0800ea33e528425fb389658806476e7defde` |

5. Run the round-5 experiments. `make reproduce` prints the commands.

The datasets are deterministic. The synthetic keys and the mixed-plane strings come from fixed seeds. The word list is `/usr/share/dict/american-english` from the `wamerican` package. Its SHA-256 is in `dbms/results/dbms_results_dictionary.json`.

## License

The code is under the MIT License (`LICENSE`). The data and the documentation are under CC BY 4.0 (`LICENSE-DATA`).
