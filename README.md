# LocaleHazard

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23103136.svg)](https://doi.org/10.5281/zenodo.23103136)

Replication package for "Correct Contract, Wrong Text: Text Roles in Locale-Sensitive Operations Across Repairs,
Static Analyzers, and PostgreSQL".

A locale-sensitive text operation can behave exactly as documented and still be wrong for the text it processes.
Turkish case mapping is correct for a Turkish word and wrong for a protocol keyword (`TITLE` → `tıtle`).
Locale-neutral mapping is the reverse. The paper calls this a contract-domain mismatch (CDM). It studies whether
repairs, static analyzers, and a database act on the role of the text.

## Quick start

```bash
python3 -m venv .venv && . .venv/bin/activate && python -m pip install -e .
make check      # unit tests of the benchmark code
make numbers    # rebuild all offline results, numbers/numbers.tex and the two generated tables
git status      # lists every deposited file that changed (expected: none)
make reproduce  # prints the commands that re-collect data or re-run tools (not run automatically)
```

`make numbers` needs Python 3.11 or later and no network. Every number in the manuscript is a macro in
`numbers/numbers.tex`.

## Reproducibility level

| Part | Level | What re-runs offline | What needs more |
|---|---|---|---|
| Construct demonstration (Section 3) | derived replay | aggregates from the 298 deposited observations | fresh run: nine toolchains (`scripts/run_benchmark.py`) |
| RQ1 repository mining | derived replay | all shares, intervals, validation and re-coding analyses, round-4 analyses | re-retrieval: GitHub token (search results drift over time) |
| RQ2 static analyzers | derived replay | verdict matrices from the recorded tool outputs (real-code scoring needs the fetched files) | re-running the tools: Maven, .NET 10 SDK, Go, Python, Node.js, clang tools, Semgrep, PMD |
| RQ3 PostgreSQL | end-to-end replay | tables and macros from the deposited results | `dbms/build_env.sh` builds PostgreSQL 18.6 and the glibc locale data from pinned sources (sha256-checked) |

Not redistributed: GitHub commit patches, the files fetched for the real-code evaluation, and the commits drawn
for the reference rate. They are third-party content, and the scripts re-fetch them by SHA. The derived per-item
tables that the analyses need are deposited.

## Map from the paper to the package

Internal file and macro names keep the original numbering: `rq3_*` = manuscript RQ1 (mining), `rq4`/`Rfour*` =
manuscript RQ2 (analyzers), `rq2`/`Rtwo*` = manuscript RQ3 (PostgreSQL). Macros `Rv*` are the round-4 additions.

| Paper | Scripts | Result files | Label |
|---|---|---|---|
| Section 3, Table 1 | `src/localehazard/analysis.py`, `mining/src/generate_numbers.py` | `out/analysis/`, `numbers/tab_rq1.tex` | planned |
| RQ1 frame, shares, Figure 3 | `mining/src/analyze_mining.py` | `mining/results/rq3_mining.json` | planned |
| RQ1 validation, recall | `mining/src/analyze_validation.py`, `post_review_rq3.py` | `rq3_validation.json`, `rq3_post_review.json` | planned / post hoc |
| RQ1 role fit, opposite direction | `analyze_ling.py`, `r3_audit_analyses.py`, `r4_rq1_analyses.py` | `rq3_ling_roles.json`, `r3_audit.json`, `r4_rq1.json` | post hoc |
| RQ1 independent re-coding | `r3_recoding.py` | `r3_recoding.json`, `validation/human/responses/` | post hoc |
| RQ1 directional contrast, query families | `r4_rq1_analyses.py` | `r4_rq1.json` | post hoc |
| RQ1 locale-test indicator | `r4_loctest_indicators.py` | `data/processed/locale_test_indicators.csv` | post hoc |
| RQ1 reference rate | `r4_reference_commits.py`, `r4_reference_analysis.py` | `data/processed/reference_commits.csv`, `r4_reference.json` | post hoc |
| RQ1 agent comparison, multi-lineage repositories | `rq3_round2.py` | `rq3_round2.json` | post hoc |
| RQ1 human coding (round 4) | `validation/human_r4/` | `results/r4_human.json` (after coding) | planned validation |
| RQ2 probes, Figure 4 | `analyzers/analyze_detectors.py` | `analyzers/results/` | planned / post hoc (context probes) |
| RQ2 real code | `r4_rq2_fetch_files.py`, `mining/scripts/r4_rq2_run_tools.sh`, `r4_rq2_score.py` | `results/r4/rq2_tools/out/`, `r4_rq2_realcode.json` | exploratory |
| RQ3 Table 3 | `dbms/run_dbms_experiment.py`, `dbms/emulation_check.py` | `dbms/results/`, `numbers/tab_rq2.tex` | planned / post hoc (two conditions) |
| RQ3 C.UTF-8 versioning | `dbms/r4_collversion_c_utf8.sh` | `mining/results/r4/rq3_collversion_c_utf8/run.log` | post hoc |
| All numbers | `mining/src/rq3_numbers.py`, `generate_numbers.py` | `numbers/numbers.tex` | |

Each round-4 result folder under `mining/results/r4/` holds `run.json` (command, input checksums, times, exit code,
and the commit of the authors' study repository) and `run.log`. Protocol, codebook and the append-only decision
log are in `mining/protocol/`. Evidence on real silent locale-data drift: `dbms/R4_SILENT_DRIFT_EVIDENCE.md`.

## Human coding (round 4)

`mining/validation/human_r4/` holds the blinded coding page and its analysis script. The key maps blinded IDs to
items and strata. It is withheld until the human coding is complete, because the strata come from the model labels.
Coders must not consult `mining/validation/`, which holds the model labels by SHA.

## RQ3: PostgreSQL

```bash
sh dbms/build_env.sh            # add --bionic on x86_64 for the real glibc 2.27 check
python3 dbms/run_dbms_experiment.py synthetic
python3 dbms/run_dbms_experiment.py dictionary
python3 dbms/emulation_check.py # needs --bionic
```

Run the experiment as a non-root user. On Ubuntu 26.04 (glibc 2.43) the rebuild reproduces every cell of Table 3
and the missed-key sets.

## License

- Code (adapters, scripts, analysis code, probes, experiment drivers, Semgrep rules): MIT, see [`LICENSE`](LICENSE).
- Data and documentation (curated records, observations, coded samples, results, recorded tool outputs, protocol
  and codebook): CC BY 4.0, see [`LICENSE-DATA`](LICENSE-DATA).
- The mined data contain commit subjects, repository names, and short code excerpts from public GitHub
  repositories. These excerpts remain under their original licenses and are included only to document and
  reproduce the analysis.

## Citation

Archived on Zenodo: [10.5281/zenodo.23103136](https://doi.org/10.5281/zenodo.23103136) (all versions). See
`CITATION.cff`.
