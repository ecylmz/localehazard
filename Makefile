# Entry points of the replication package.
#   make numbers    rebuilds every result file that can be rebuilt offline from the deposited data, then the
#                   manuscript macros (numbers/numbers.tex) and the two generated tables. No network, no paid calls.
#                   Afterwards `git status` lists every deposited file that changed (expected: none); outside a git
#                   checkout this step is skipped.
#   make reproduce  prints the commands that re-collect data or re-run the tools (network, GitHub token, Docker,
#                   toolchains). They are not run automatically.
PY ?= python3

.PHONY: numbers reproduce check
numbers:
	PYTHONPATH=src $(PY) -m localehazard.analysis --check > /dev/null
	cd mining && $(PY) src/analyze_mining.py > /dev/null
	cd mining && $(PY) src/analyze_validation.py > /dev/null
	cd mining && $(PY) src/analyze_ling.py > /dev/null
	cd mining && $(PY) src/role_heuristic_eval.py > /dev/null
	cd mining && $(PY) src/post_review_rq3.py > /dev/null
	cd mining && $(PY) src/r3_audit_analyses.py > /dev/null
	cd mining && $(PY) src/r3_recoding.py > /dev/null
	cd mining && $(PY) src/rq3_round2.py > /dev/null
	cd mining && $(PY) src/r4_rq1_analyses.py > /dev/null
	cd mining && $(PY) src/r4_reference_analysis.py > /dev/null
	cd mining && $(PY) validation/human_r4/analyze_human_r4.py validation/human_r4/responses/human_coding_H1_2026-11-09.csv validation/human_r4/responses/human_coding_H2_2026-11-09.csv validation/human_r4/responses/human_coding_reconciled_2026-11-11.csv > /dev/null
	$(PY) analyzers/analyze_detectors.py > /dev/null
	cd mining && $(PY) src/rq3_numbers.py > /dev/null
	cd mining && $(PY) src/generate_numbers.py
	@if [ -d .git ]; then git status --short; else echo "(no .git: compare the outputs with the archived files)"; fi

check:
	PYTHONPATH=src $(PY) -m unittest discover -s tests -v

reproduce:
	@echo "Re-collection and tool runs (see README.md for prerequisites):"
	@echo "  RQ1 mining:      cd mining && python3 src/retrieve_commits.py && python3 src/fetch_details.py && python3 src/classify_diffs.py"
	@echo "  RQ1 indicators:  cd mining && python3 src/r4_loctest_indicators.py          # needs the patches fetched above"
	@echo "  RQ1 reference:   cd mining && python3 src/r4_reference_commits.py           # GitHub API, about 2 hours"
	@echo "  RQ2 real code:   cd mining && python3 src/r4_rq2_fetch_files.py && sh scripts/r4_rq2_run_tools.sh data/raw/r4/realcode results/r4/rq2_tools/out && python3 src/r4_rq2_run_dotnet.py data/raw/r4/realcode results/r4/rq2_dotnet/out && python3 src/r4_rq2_score.py results/r4/rq2_tools/out results/r4/rq2_dotnet/out"
	@echo "  RQ2 probes:      see analyzers/ (Maven, .NET 10 SDK, Go, Python, Node.js, clang tools)"
	@echo "  RQ3 PostgreSQL:  sh dbms/build_env.sh [--bionic] && python3 dbms/run_dbms_experiment.py synthetic && python3 dbms/run_dbms_experiment.py dictionary"
	@echo "  RQ3 C.UTF-8:     sh dbms/r4_collversion_c_utf8.sh"
	@echo "  Benchmark:       ./scripts/build_adapters.sh && python3 scripts/run_benchmark.py"
