#!/bin/bash
# Re-run single fetch rounds under a timeout until retrieval is complete and nothing is left to fetch.
cd "$(dirname "$0")/.."
while true; do
  timeout 900 python3 src/fetch_details.py >> logs/fetch_stdout.log 2>&1
  if grep -q ALLDONE logs/retrieve_commits.log; then
    left=$(python3 -c "
import sys; sys.path.insert(0,'src'); import fetch_details as f
c=f.candidates(); print(sum(1 for r in c.values() if not (f.CDIR/(r['sha']+'.json.gz')).exists()))")
    repos_left=$(python3 -c "
import sys; sys.path.insert(0,'src'); import fetch_details as f
c=f.candidates(); print(sum(1 for n in {r['repo'] for r in c.values()} if not (f.RDIR/(n.replace('/','__')+'.json')).exists()))")
    echo "WATCHDOG left=$left repos_left=$repos_left" >> logs/fetch_details.log
    if [ "$left" = "0" ]; then echo FETCH_DONE >> logs/fetch_details.log; break; fi
  fi
  sleep 5
done
