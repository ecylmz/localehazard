import json, subprocess, time, sys
qs = sys.argv[1:]
for q in qs:
    r = subprocess.run(["gh","api","-X","GET","search/commits","-f",f"q={q}","-f","per_page=1"],capture_output=True,text=True)
    try: c=json.loads(r.stdout)["total_count"]
    except Exception: c=r.stdout[:200]+r.stderr[:200]
    print(f"{c}\t{q}", flush=True); time.sleep(2.1)
