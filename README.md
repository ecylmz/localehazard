# LocaleHazard

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23103136.svg)](https://doi.org/10.5281/zenodo.23103136)

Replication package for **"Correct Contract, Wrong Text: Text Roles in Locale-Sensitive Operations Across Repairs, Static Analyzers, and PostgreSQL"**.

A locale-sensitive text operation can behave exactly as documented and still be wrong for the text it processes: Turkish case mapping is correct for a Turkish word and wrong for a protocol keyword (`TITLE` → `tıtle`), and locale-neutral mapping is the reverse. The paper calls this a *contract–domain mismatch* (CDM) and studies whether repairs, static analyzers, and a database act on the role of the text.

| Part | Directory | What it contains |
|---|---|---|
| Construct demonstration (Section 3) | `adapters/`, `contracts/`, `scenarios/`, `data/`, `scripts/`, `src/` | Controlled benchmark: 42 API contracts in nine ecosystems, 21 cases, 298 frozen observations, standards-oracle checks |
| RQ1 — repository mining | `mining/` | GitHub commit-search queries and retrieval, diff classifier (frozen v1 and corrected v2), deduplicated repair lineages, coded validation samples, analysis scripts and results |
| RQ2 — static analyzers | `analyzers/` | Role-paired and context-bearing probes in Java, C#, Go, Python, JavaScript, and C; recorded outputs of twelve analyzers and Semgrep; dynamic label checks; role-aware Semgrep prototype |
| RQ3 — PostgreSQL | `dbms/` | Experiment driver for a glibc collation-data change under existing B-tree indexes, version shim, validation against a real glibc 2.27 runtime, results and raw `psql` outputs |

Protocol, codebook, and an append-only log of every deviation are in `mining/protocol/`.

## Construct demonstration

Requires Python 3.11+. Re-executing the benchmark additionally needs GCC with ICU development libraries, .NET, Go, a JDK, Node.js, PHP with `intl`, Ruby, Rust, and the `tr_TR`, `en_US`, and `C` UTF-8 locales.

```bash
python -m venv .venv && . .venv/bin/activate && python -m pip install -e .
localehazard-analyze --check            # recompute aggregates from data/controlled/
python -m unittest discover -s tests -v
./scripts/build_adapters.sh && python scripts/run_benchmark.py   # optional fresh run (writes out/)
```

## RQ1: repository mining (`mining/`)

The aggregate analyses run offline from the included data:

```bash
python mining/src/analyze_mining.py       # lineages, shares, repository-clustered bootstrap
python mining/src/analyze_validation.py   # inter-coder agreement, precision, missed repairs
python mining/src/analyze_ling.py         # role coding of opposite-direction repairs
python mining/src/role_heuristic_eval.py  # line-level role cues against coded roles
```

Included data:

- `data/raw/search/*.meta.json`: per-query and per-slice totals.
- `data/raw/search_hits.csv.gz`: every retrieved hit, with commit subject and SHA.
- `data/processed/`: classified commits, repaired call sites, lineages, and residual-call counts.
- `validation/`: blinded coding items, both coders' labels, and adjudication.

Raw API responses and commit patches are not redistributed. To rebuild them from GitHub (requires `gh auth login`), run the first two scripts, then reclassify:

```bash
python mining/src/retrieve_commits.py      # GitHub commit search (queries: protocol/mining_queries.json)
python mining/src/fetch_details.py         # patches by SHA into data/raw/commits/
python mining/src/classify_diffs.py        # diff-based classifier
```

Three scripts need these patches: `classify_diffs.py`, `post_review_rq3.py` (locale-specific test lines), and `residual_sites.py`. GitHub search results change over time, so the included hit list is the authoritative frame.

## RQ2: static analyzers (`analyzers/`)

- `probes.json`: probe roles and labels.
- `*/out/`: the recorded tool outputs.
- `dyn_*.tsv`: dynamic checks of every probe under a Turkish locale.

Rebuild the verdict matrix from the recorded outputs with:

```bash
python analyzers/analyze_detectors.py
```

To re-run the tools you need Maven with Error Prone 2.50.0, SpotBugs 4.10.4, PMD 7.28.0, and forbidden-apis 3.11 (configured in `java/pom.xml`), plus the following:

| Tool | Command |
|---|---|
| .NET 10 SDK | `dotnet build` (`AnalysisLevel=latest-all`) |
| staticcheck | `staticcheck -checks all` |
| Ruff | `ruff check --select ALL` |
| Pylint | `pylint --enable=all` |
| ESLint | `npx eslint` |
| clang-tidy | `clang-tidy --checks='*'` |
| Cppcheck | `cppcheck --enable=all` |
| Semgrep | `semgrep scan --config p/default …` |
| Role-aware prototype | `semgrep scan --config semgrep/role_aware_prototype.yml` |

## RQ3: PostgreSQL (`dbms/`)

1. Build PostgreSQL 18.6 from source into `dbms/pg` with ICU and contrib (`amcheck`, `citext`).
2. Compile `en_US.UTF-8` and `tr_TR.UTF-8` with `localedef` into three directories: `dbms/loc/old` (from the glibc-2.27 `localedata`), `dbms/loc/v228` (from glibc-2.28), and `dbms/loc/new` (host data).
3. Build the version shim: `gcc -shared -fPIC -o dbms/libcver_shim.so dbms/libcver_shim.c`.
4. Run the experiment:
   ```bash
   python dbms/run_dbms_experiment.py synthetic
   python dbms/run_dbms_experiment.py dictionary
   ```
   Each run covers four conditions: drift (2.43 data), drift to 2.28, silent drift (the data change but the reported version does not), and stable.
5. Optionally, check the emulation against a real glibc 2.27 runtime with `dbms/emulation_check.py`. It uses the Ubuntu 18.04 base image extracted to `dbms/bionic`.

The results are in `dbms/results/dbms_results_*.json`, with the raw `psql` output for each step in `dbms/results/raw_*`.

## Citation

Archived on Zenodo: [10.5281/zenodo.23103136](https://doi.org/10.5281/zenodo.23103136) (all versions; v2.0.0 is [10.5281/zenodo.23103137](https://doi.org/10.5281/zenodo.23103137)). See `CITATION.cff`.
