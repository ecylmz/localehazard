# LocaleHazardBench

LocaleHazardBench is the replication package for a cross-ecosystem study of locale-sensitive text semantics and API-contract/domain mismatch. It contains the controlled scenarios, curated API-contract and defect evidence, ecosystem adapters, frozen observations, aggregate-analysis code, and consistency tests needed to inspect or reproduce the computational results.

## Requirements

Aggregate analysis requires Python 3.11 or newer. Re-executing the complete controlled benchmark additionally requires GCC with ICU development libraries, .NET, Go, a JDK, Node.js, PHP with `intl`, Ruby, Rust, and the `tr_TR`, `en_US`, and `C` UTF-8 locales.

## Installation

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e .
```

## Running the controlled benchmark

```bash
./scripts/build_adapters.sh
python scripts/smoke_adapters.py
python scripts/run_benchmark.py
python scripts/run_standards_validation.py
```

Generated records are written below `out/` and are not tracked. Runtime and locale versions can affect a fresh execution; the paper's frozen observations remain in `data/controlled/`.

## Reproducing aggregate analysis

```bash
localehazard-analyze --check
python -m unittest discover -s tests -v
```

The analysis writes JSON and CSV outputs below `out/analysis/`.

## Repository structure

- `adapters/`: ecosystem-specific benchmark adapters
- `scenarios/` and `contracts/`: controlled cases and curated API-contract metadata
- `data/controlled/`: frozen controlled and standards-oracle observations
- `data/defects/`: screened candidates, retained defects, coding, and correspondence evidence
- `scripts/`: adapter build, smoke, benchmark, and standards runners
- `src/localehazard/`: aggregate analysis and consistency checks
- `tests/`: deterministic unit and smoke tests

## Citation

Citation metadata is provided in `CITATION.cff`. No DOI is currently assigned.
