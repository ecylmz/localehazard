from __future__ import annotations
import base64,csv,json,subprocess,sys,unicodedata
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];B=lambda s:base64.b64encode(s.encode()).decode();cases=[json.loads(x) for x in (ROOT/'data/standards/cases.jsonl').read_text(encoding='utf-8').splitlines()]
CMD={'C':[str(ROOT/'build/c_adapter')],'Java':['java','-cp',str(ROOT/'build/java'),'JavaAdapter'],'Node':['node',str(ROOT/'adapters/node_adapter.js')],'Python':[sys.executable,str(ROOT/'adapters/python_adapter.py')],'Ruby':['ruby',str(ROOT/'adapters/ruby_adapter.rb')],'DotNet':['dotnet',str(ROOT/'build/dotnet/DotnetAdapter.dll')],'PHP':['php',str(ROOT/'adapters/php_adapter.php')]}
def call(eco,var,op,loc,x,y=''):
 p=subprocess.run(CMD[eco]+[var,op,loc,B(x)]+([B(y)]if y else[]),text=True,capture_output=True,timeout=30)
 try:o=json.loads(p.stdout)
 except:o={'status':'execution_error','error':p.stderr or p.stdout}
 if o.get('kind')=='string':o['actual']=base64.b64decode(o['value_b64']).decode()
 else:o['actual']=o.get('value')
 return o
rows=[]
for c in cases:
 targets=[]
 if c['operation'] in {'lower','upper'}:
  targets=[('C','icu_locale',True),('Java','explicit_locale',True),('Node','explicit_locale',True)]
  if c['locale'] in {'tr','az'}:targets.append(('Ruby','turkic',c['control_class']!='contextual_special_casing'))
 elif c['operation']=='fold':
  if c['locale']=='root':targets=[('Python','casefold',True),('Ruby','fold',True)]
  else:targets=[]
 elif c['operation']=='collate_relation':targets=[('C','icu_collator',True),('Java','collator',False),('Node','collator',True),('DotNet','culture_compare',False),('PHP','collator',True)]
 elif c['operation'].startswith('normalize_'):
  # Generator/oracle self-check; cross-ecosystem canonical-equivalence checks are CDM12/CDM13.
  form='NFC' if c['operation']=='normalize_nfc' else 'NFD';actual=unicodedata.normalize(form,c['input']);rows.append({**c,'ecosystem':'GeneratorSelfCheck','api_id':f'unicodedata.{form}','actual':actual,'standards_oracle_status':'conformant' if actual==c['expected'] else 'nonconformant','effective_locale':'root'});continue
 for eco,var,standards_applicable in targets:
  op='compare_relation' if c['operation']=='collate_relation' else c['operation'];o=call(eco,var,op,c['locale'],c['input'],c.get('input2',''));expected=int(c['expected']) if op=='compare_relation' else c['expected'];status=o.get('status');actual=o.get('actual')
  oracle='not_applicable' if not standards_applicable else ('conformant' if status=='ok' and actual==expected else status if status!='ok' else 'nonconformant')
  rows.append({**c,'ecosystem':eco,'api_id':var,'actual':actual,'standards_oracle_status':oracle,'effective_locale':o.get('effective_locale',''),'error':o.get('error','')})
out=ROOT/'out/standards';out.mkdir(parents=True,exist_ok=True);fields=[]
for r in rows:
 for k in r:
  if k not in fields:fields.append(k)
with (out/'standards_validation.csv').open('w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
summary={'n_generated_cases':len(cases),'n_validation_observations':len(rows),'outcomes':dict(Counter(r['standards_oracle_status'] for r in rows)),'by_ecosystem':{e:dict(Counter(r['standards_oracle_status'] for r in rows if r['ecosystem']==e)) for e in sorted(set(r['ecosystem'] for r in rows))}}
(out/'standards_validation_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2,sort_keys=True),encoding='utf-8');print(json.dumps(summary,ensure_ascii=False,indent=2))
