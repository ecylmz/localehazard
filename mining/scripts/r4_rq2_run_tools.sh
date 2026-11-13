#!/bin/sh
# Round-4 RQ2 real-code evaluation, step 2 (exploratory; protocol/DEVIATIONS.md, 2026-11-09).
# Runs, in Docker, on the pre/post files fetched by src/r4_rq2_fetch_files.py:
#   - the six prototype rules (detectors/semgrep/role_aware_prototype.yml), Semgrep 1.179.0 as in RQ2;
#   - the Semgrep registry packs used in RQ2 that cover these languages (p/default, p/java, p/csharp,
#     p/javascript, p/typescript); the registry is downloaded at run time, so its rule set is the current one;
#   - PMD 7.28.0 with UseLocaleWithCaseConversions, the only PMD rule in the RQ2 relevance list.
# Usage: sh scripts/r4_rq2_run_tools.sh <realcode_dir> <out_dir>
set -eu
SRC=$(cd "$1" && pwd)
OUT=$2; mkdir -p "$OUT"; OUT=$(cd "$OUT" && pwd)
R=$(dirname "$0")
if [ -d "$R/../detectors/semgrep" ]; then RULES=$(cd "$R/../detectors/semgrep" && pwd)  # study layout
else RULES=$(cd "$R/../../analyzers/semgrep" && pwd); fi                            # package layout
SG=semgrep/semgrep:1.179.0
PMDV=7.28.0

docker run --rm -v "$SRC":/src:ro -v "$RULES":/rules:ro -v "$OUT":/out "$SG" \
  semgrep scan --metrics=off --no-git-ignore --config /rules/role_aware_prototype.yml --json -o /out/semgrep_prototype.json /src \
  > "$OUT/semgrep_prototype.log" 2>&1
docker run --rm -v "$SRC":/src:ro -v "$OUT":/out "$SG" \
  semgrep scan --metrics=off --no-git-ignore --config p/default --config p/java --config p/csharp --config p/javascript \
  --config p/typescript --json -o /out/semgrep_registry.json /src > "$OUT/semgrep_registry.log" 2>&1
docker run --rm "$SG" semgrep --version > "$OUT/semgrep_version.txt"

if [ ! -d "$OUT/tools/pmd-bin-$PMDV" ]; then
  mkdir -p "$OUT/tools"
  curl -sSL -o "$OUT/tools/pmd.zip" "https://github.com/pmd/pmd/releases/download/pmd_releases%2F$PMDV/pmd-dist-$PMDV-bin.zip"
  (cd "$OUT/tools" && unzip -q pmd.zip && rm pmd.zip)
fi
docker run --rm -v "$SRC":/src:ro -v "$OUT":/out eclipse-temurin:21-jre \
  /out/tools/pmd-bin-$PMDV/bin/pmd check --no-cache --no-progress -d /src \
  -R category/java/errorprone.xml/UseLocaleWithCaseConversions -f json -r /out/pmd.json > "$OUT/pmd.log" 2>&1 || test $? -eq 4  # 4 = violations found
echo "pmd $PMDV" >> "$OUT/semgrep_version.txt"
ls -la "$OUT"
