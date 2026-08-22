from __future__ import annotations
import base64,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
B=lambda s:base64.b64encode(s.encode()).decode()
commands={
 "C":[str(ROOT/'build/c_adapter')],"DotNet":['dotnet',str(ROOT/'build/dotnet/DotnetAdapter.dll')],"Go":[str(ROOT/'build/go_adapter')],"Java":['java','-cp',str(ROOT/'build/java'),'JavaAdapter'],"Node":['node',str(ROOT/'adapters/node_adapter.js')],"PHP":['php',str(ROOT/'adapters/php_adapter.php')],"Python":[sys.executable,str(ROOT/'adapters/python_adapter.py')],"Ruby":['ruby',str(ROOT/'adapters/ruby_adapter.rb')],"Rust":[str(ROOT/'build/rust_adapter')]
}
tests=[
 ("C","icu_locale","lower","tr-TR","I","","ı"),("C","ascii","native_lower","tr_TR.utf8","INIT","","init"),
 ("DotNet","explicit_culture","upper","tr-TR","i","","İ"),("Go","turkic_special","lower","tr-TR","I","","ı"),
 ("Java","explicit_locale","lower","tr-TR","I","","ı"),("Node","explicit_locale","upper","tr-TR","i","","İ"),
 ("PHP","unicode_default","lower","root","I","","i"),("Python","unicode_default","lower","root","I","","i"),
 ("Ruby","turkic","lower","tr-TR","I","","ı"),("Rust","unicode_default","lower","root","I","","i")]
rows=[]
for eco,var,op,loc,x,y,exp in tests:
 p=subprocess.run(commands[eco]+[var,op,loc,B(x)]+([B(y)] if y else []),text=True,capture_output=True,timeout=30)
 try:o=json.loads(p.stdout)
 except Exception:raise SystemExit(f"{eco}: invalid JSON stdout={p.stdout!r} stderr={p.stderr!r}")
 got=base64.b64decode(o['value_b64']).decode() if o.get('kind')=='string' else o.get('value')
 rows.append({'ecosystem':eco,'status':o.get('status'),'got':got,'expected':exp,'pass':p.returncode==0 and got==exp})
if not all(r['pass'] for r in rows):print(json.dumps(rows,ensure_ascii=False,indent=2));raise SystemExit(1)
print(json.dumps({'adapter_smoke_tests':'pass','n':len(rows),'rows':rows},ensure_ascii=False,indent=2))
