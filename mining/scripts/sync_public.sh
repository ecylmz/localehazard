#!/bin/sh
# Sync the study repository (study2/) into the public replication package (localehazard-public/, branch r4-revision).
# Mapping: study2/{src,protocol,validation,results,data/processed,scripts} -> mining/...; study2/dbms -> dbms (scripts,
# results, small inputs); study2/detectors -> analyzers (results only). Raw third-party data stay out (patches,
# fetched source files, reference commits). Coder first names are replaced by the coder codes H1 and H2.
set -eu
ST=$HOME/github/ecylmz/in-progress/localehazard/study2
PU=$HOME/github/ecylmz/in-progress/localehazard-public
EX="--exclude=__pycache__ --exclude=*.pyc"
rsync -a $EX "$ST/src/" "$PU/mining/src/"
rsync -a --exclude=AMENDMENT_A2.md "$ST/protocol/" "$PU/mining/protocol/"  # the public amendment is the edited version
rsync -a $EX "$ST/validation/" "$PU/mining/validation/"
sed -i "s/\(H[12]\) ([^)]*)/\1/g" "$PU/mining/validation/human_r4/for_coders/uzlasma.html" "$PU/mining/validation/human_r4/build_reconcile_page_r4.py"
sed -i "s/H1 = [^,]* (the author), H2 = [^.]*\./H1 = the author, H2 = a second coder./" "$PU/mining/protocol/DEVIATIONS.md"
rsync -a "$ST/results/" "$PU/mining/results/"
mkdir -p "$PU/mining/scripts" "$PU/mining/docs"
rsync -a "$ST/scripts/" "$PU/mining/scripts/"
for f in locale_test_indicators.csv realcode_files.csv reference_commits.csv commits_classified.csv commits_lineages.csv repair_edits.csv residual_sites.csv; do
  [ -f "$ST/data/processed/$f" ] && cp "$ST/data/processed/$f" "$PU/mining/data/processed/$f"
done
cp "$ST/literature/R4_SILENT_DRIFT_EVIDENCE.md" "$PU/dbms/"
cp "$ST/dbms/build_env.sh" "$ST/dbms/r4_collversion_c_utf8.sh" "$ST/dbms/run_dbms_experiment.py" "$ST/dbms/emulation_check.py" "$ST/dbms/libcver_shim.c" "$PU/dbms/"
for d in raw_synthetic raw_dictionary; do mkdir -p "$PU/dbms/results/$d"; cp "$ST/dbms/results/$d/dataset.csv" "$PU/dbms/results/$d/"; done
rsync -a "$ST/detectors/results/" "$PU/analyzers/results/"
cd "$PU" && git status --short | wc -l
