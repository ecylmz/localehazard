"""Bounded GitHub commit-search retrieval for RQ3 (protocol/mining_queries.json)."""
import json, subprocess, time, sys, os, datetime, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
P = json.load(open(ROOT/"protocol/mining_queries.json"))
OUT = ROOT/"data/raw/search"; OUT.mkdir(parents=True, exist_ok=True)
(ROOT/"logs").mkdir(exist_ok=True)
LOG = open(ROOT/"logs/retrieve_commits.log","a")
def log(*a):
    s=" ".join(str(x) for x in a); print(s, flush=True); LOG.write(s+"\n"); LOG.flush()
def call(q, page, per_page=100):
    delay=60
    while True:
        r=subprocess.run(["gh","api","-X","GET","search/commits","-f",f"q={q}","-f",f"per_page={per_page}","-f",f"page={page}"],capture_output=True,text=True)
        time.sleep(6.5)
        if r.returncode==0:
            return json.loads(r.stdout)
        msg=(r.stdout+r.stderr)[:300]
        if "rate limit" in msg.lower() or "abuse" in msg.lower() or "403" in msg or "502" in msg or "timeout" in msg.lower():
            log("BACKOFF",delay,q,page,msg.replace("\n"," ")[:120]); time.sleep(delay); delay=min(delay*2,600); continue
        if "Cannot access beyond the first 1000" in msg or "422" in msg:
            log("STOP422",q,page,msg[:120]); return None
        log("ERROR",q,page,msg[:200]); time.sleep(30); delay=60
def keep(it):
    c=it["commit"]; rp=it["repository"]
    return {"sha":it["sha"],"repo":rp["full_name"],"fork":rp.get("fork"),"html_url":it.get("html_url"),
            "message":c["message"],"author_date":c["author"]["date"] if c.get("author") else None,
            "committer_date":c["committer"]["date"] if c.get("committer") else None,
            "parents":len(it.get("parents",[]))}
def quarters(a,b):
    y,m=int(a[:4]),1
    end=datetime.date.fromisoformat(b)
    while True:
        s=datetime.date(y,m,1)
        if s>end: break
        nm=m+3; ny=y+(nm>12); nm=nm-12 if nm>12 else nm
        e=min(datetime.date(ny,nm,1)-datetime.timedelta(days=1),end)
        yield s.isoformat(),e.isoformat(); y,m=ny,nm
def run():
    a,b=P["window"]
    for Q in P["queries"]:
        f=OUT/f"{Q['id']}.jsonl"
        if (OUT/f"{Q['id']}.done").exists(): log("SKIP",Q["id"]); continue
        try:
            fd=os.open(OUT/f"{Q['id']}.lock", os.O_CREAT|os.O_EXCL|os.O_WRONLY); os.close(fd)
        except FileExistsError:
            log("LOCKED",Q["id"]); continue
        fh=open(f,"w"); meta={"id":Q["id"],"q":Q["q"],"slices":[]}
        base=f"{Q['q']} committer-date:{a}..{b}"
        d=call(base,1,1); tot=d["total_count"] if d else 0
        meta["total_count"]=tot; log("QUERY",Q["id"],tot)
        if tot<=1000:
            for p in range(1,(tot+99)//100+1):
                d=call(base,p)
                if not d: break
                for it in d["items"]: fh.write(json.dumps({**keep(it),"query":Q["id"],"slice":"all","page":p})+"\n")
            meta["slices"].append({"slice":"all","total":tot,"pages":(tot+99)//100})
        else:
            for s,e in quarters(a,b):
                q=f"{Q['q']} committer-date:{s}..{e}"
                d=call(q,1)
                if not d: continue
                for it in d["items"]: fh.write(json.dumps({**keep(it),"query":Q["id"],"slice":s,"page":1})+"\n")
                meta["slices"].append({"slice":s,"total":d["total_count"],"retrieved":len(d["items"])})
        fh.close(); json.dump(meta,open(OUT/f"{Q['id']}.meta.json","w"),indent=1)
        (OUT/f"{Q['id']}.done").write_text(datetime.datetime.utcnow().isoformat())
    if all((OUT/f"{Q['id']}.done").exists() for Q in P["queries"]): log("ALLDONE")
run()
