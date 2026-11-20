# make numbers   rebuilds the paper's macros and its two tables from the deposited results (Python 3, standard
#                library only, no network). The outputs go to numbers/. In a git checkout, `git status` afterwards
#                lists every deposited file that changed (expected: none).
# make reproduce prints the commands that rerun the experiments. They need Linux on x86_64, a C toolchain,
#                Docker, and a few gigabytes of disk space. They are not run automatically.
PY ?= python3

.PHONY: numbers reproduce
numbers:
	$(PY) src/r4_numbers.py numbers
	$(PY) src/r5_numbers.py numbers
	@if [ -d .git ]; then git status --short; else echo "(no .git: compare numbers/ with the archived copy)"; fi

reproduce:
	@echo "Environment:        sh dbms/build_env.sh --bionic"
	@echo "Emulated drift:     python3 dbms/run_dbms_experiment.py synthetic && python3 dbms/run_dbms_experiment.py dictionary"
	@echo "Emulation check:    python3 dbms/emulation_check.py"
	@echo "Version check:      sh dbms/r4_collversion_c_utf8.sh"
	@echo "Repair paths:       python3 dbms/r5_repair.py synthetic results/r5/repair_synthetic && python3 dbms/r5_repair.py dictionary results/r5/repair_dictionary"
	@echo "Turkish matrix:     python3 dbms/r5_turkish.py results/r5/turkish"
	@echo "C.UTF-8 order:      python3 dbms/r5_cutf8_order.py results/r5/cutf8_order   # needs dbms/rootfs/focal and dbms/rootfs/jammy (README)"
	@echo "Real upgrades:      python3 dbms/r5_real_upgrade.py results/r5/real_upgrade  # needs the Docker images lh-pg186:* (README)"
