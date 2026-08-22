from __future__ import annotations
import base64,csv,hashlib,json,os,platform,subprocess,sys,time,unicodedata
from collections import Counter,defaultdict
from datetime import datetime,timezone
from itertools import combinations
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SCENARIOS=json.loads((ROOT/'scenarios/cases.json').read_text(encoding='utf-8'))
BUILD=ROOT/'build'
B=lambda s:base64.b64encode(s.encode()).decode()
CP=lambda s:' '.join(f'U+{ord(c):04X}' for c in s)
ESC=lambda s:''.join(c if 0x20<=ord(c)<=0x7e else f'\\u{{{ord(c):04X}}}' for c in s)

COMMANDS={
 'C':[str(BUILD/'c_adapter')], 'DotNet':['dotnet',str(BUILD/'dotnet/DotnetAdapter.dll')],
 'Go':[str(BUILD/'go_adapter')], 'Java':['java','-cp',str(BUILD/'java'),'JavaAdapter'],
 'Node':['node',str(ROOT/'adapters/node_adapter.js')], 'PHP':['php',str(ROOT/'adapters/php_adapter.php')],
 'Python':[sys.executable,str(ROOT/'adapters/python_adapter.py')], 'Ruby':['ruby',str(ROOT/'adapters/ruby_adapter.rb')],
 'Rust':[str(BUILD/'rust_adapter')]
}

VARIANTS=[
 # ecosystem, variant, operations, contract mode, API class, granularity, backend, standards applicability
 ('C','icu_locale',{'lower','upper'},'locale_full','explicit_locale_aware','full_string','icu_direct_or_bundled',True),
 ('C','icu_root',{'lower','upper'},'default_full','invariant_root','full_string','icu_direct_or_bundled',True),
 ('DotNet','explicit_culture',{'lower','upper'},'dotnet_locale','explicit_locale_aware','full_string','dotnet_globalization',False),
 ('DotNet','current_culture',{'lower','upper'},'dotnet_locale','default_locale_sensitive','full_string','dotnet_globalization',False),
 ('DotNet','invariant',{'lower','upper'},'dotnet_invariant','invariant_root','full_string','dotnet_globalization',False),
 ('Go','unicode_default',{'lower','upper'},'go_simple','unicode_defined','simple_code_point','runtime_unicode_tables',True),
 ('Go','turkic_special',{'lower','upper'},'turkic_simple','explicit_locale_aware','simple_code_point','runtime_unicode_tables',True),
 ('Java','explicit_locale',{'lower','upper'},'locale_full','explicit_locale_aware','full_string','jdk_locale_provider',True),
 ('Java','default_locale',{'lower','upper'},'locale_full','default_locale_sensitive','full_string','jdk_locale_provider',True),
 ('Java','root',{'lower','upper'},'default_full','invariant_root','full_string','jdk_locale_provider',True),
 ('Node','explicit_locale',{'lower','upper'},'locale_full','explicit_locale_aware','full_string','icu_direct_or_bundled',True),
 ('Node','unicode_default',{'lower','upper'},'default_full','unicode_defined','full_string','runtime_unicode_tables',True),
 ('PHP','unicode_default',{'lower','upper'},'default_full','unicode_defined','full_string','external_unicode_library',True),
 ('Python','unicode_default',{'lower','upper'},'default_full','unicode_defined','full_string','runtime_unicode_tables',True),
 ('Ruby','unicode_default',{'lower','upper'},'default_full','unicode_defined','full_string','runtime_unicode_tables',True),
 ('Ruby','turkic',{'lower','upper'},'turkic_full','explicit_locale_aware','full_string','runtime_unicode_tables',True),
 ('Ruby','ascii',{'lower','upper'},'ascii','ordinal_canonical','simple_code_point','runtime_unicode_tables',False),
 ('Rust','unicode_default',{'lower','upper'},'default_full','unicode_defined','full_string','runtime_unicode_tables',True),
 ('Rust','ascii',{'lower','upper'},'ascii','ordinal_canonical','simple_code_point','runtime_unicode_tables',False),
 ('C','icu_collator',{'compare_equal'},'locale_collator','explicit_locale_aware','not_applicable','icu_direct_or_bundled',True),
 ('DotNet','culture_compare',{'compare_equal'},'locale_collator','explicit_locale_aware','not_applicable','dotnet_globalization',False),
 ('DotNet','ordinal_ignore_case',{'compare_equal'},'ordinal_ignore','ordinal_canonical','not_applicable','dotnet_globalization',False),
 ('Go','equal_fold',{'compare_equal'},'unicode_fold','unicode_defined','not_applicable','runtime_unicode_tables',True),
 ('Java','collator',{'compare_equal'},'locale_collator','explicit_locale_aware','not_applicable','jdk_locale_provider',False),
 ('Java','equals_ignore_case',{'compare_equal'},'java_ignore','unicode_defined','not_applicable','runtime_unicode_tables',False),
 ('Node','collator',{'compare_equal'},'locale_collator','explicit_locale_aware','not_applicable','icu_direct_or_bundled',True),
 ('PHP','collator',{'compare_equal'},'locale_collator','explicit_locale_aware','not_applicable','icu_direct_or_bundled',True),
 ('Python','casefold',{'compare_equal'},'unicode_fold','unicode_defined','not_applicable','runtime_unicode_tables',True),
 ('Python','locale_collator',{'compare_equal'},'locale_collator','default_locale_sensitive','not_applicable','libc_glibc',False),
 ('Ruby','casecmp',{'compare_equal'},'unicode_fold','unicode_defined','not_applicable','runtime_unicode_tables',True),
 ('Rust','ascii_compare',{'compare_equal'},'ascii_ignore','ordinal_canonical','not_applicable','runtime_unicode_tables',False),
]
NORMALIZERS=[
 ('C','icu_normalizer','icu_direct_or_bundled',True),('DotNet','normalizer','dotnet_globalization',False),
 ('Go','normalizer','runtime_unicode_tables',False),('Java','normalizer','runtime_unicode_tables',True),
 ('Node','normalizer','runtime_unicode_tables',True),('PHP','normalizer','icu_direct_or_bundled',True),
 ('Python','normalizer','runtime_unicode_tables',True),('Ruby','normalizer','runtime_unicode_tables',True),
 ('Rust','normalizer','runtime_unicode_tables',False)]
COLLATION_PROVIDERS=[
 ('C','icu_collator','tr-TR','icu_direct_or_bundled'),('DotNet','culture_compare','tr-TR','dotnet_globalization'),
 ('Java','collator','tr-TR','jdk_locale_provider'),('Node','collator','tr-TR','icu_direct_or_bundled'),
 ('PHP','collator','tr-TR','icu_direct_or_bundled'),('Python','locale_collator','tr_TR.utf8','libc_glibc')]

def firstline(cmd):
 p=subprocess.run(cmd,text=True,capture_output=True,timeout=20);return (p.stdout or p.stderr).strip().splitlines()[0] if (p.stdout or p.stderr).strip() else ''
def versions():
 node=json.loads(subprocess.run(['node','-e','console.log(JSON.stringify(process.versions))'],text=True,capture_output=True,check=True).stdout)
 return {'C':firstline(['gcc','--version']),'DotNet':firstline(['dotnet','--version']),'Go':firstline(['go','version']),'Java':firstline(['java','-version']),'Node':node['node'],'PHP':firstline(['php','--version']),'Python':platform.python_version(),'Ruby':firstline(['ruby','--version']),'Rust':firstline(['rustc','--version']),'node_components':node,'python_unidata':unicodedata.unidata_version,'icu':firstline(['pkg-config','--modversion','icu-uc']),'libc':firstline(['ldd','--version'])}
VERS=versions()

def invoke(eco,var,op,loc,x,y=''):
 cmd=COMMANDS[eco]+[var,op,loc,B(x)]+([B(y)] if y!='' else [])
 t=time.monotonic();p=subprocess.run(cmd,text=True,capture_output=True,timeout=30);ms=round((time.monotonic()-t)*1000,3)
 try:o=json.loads(p.stdout)
 except Exception:o={'status':'execution_error','error':f'invalid_json:{p.stdout[:200]}'}
 o.update({'exit_code':p.returncode,'stderr':p.stderr,'duration_ms':ms,'command':cmd[:3]+['<encoded-input>']})
 if o.get('kind')=='string':o['actual']=base64.b64decode(o['value_b64']).decode()
 elif o.get('kind') in {'bool','int'}:o['actual']=o.get('value')
 return o

DEFAULT={'CDM01':'i','CDM02':'I','CDM03':'i','CDM04':'i\u0301','CDM05':'title','CDM06':'APPLICATION','CDM07':'file','CDM08':'i\u0307','CDM20':'hello','CDM21':'123-_'}
TAILORED={'CDM01':'ı','CDM02':'İ','CDM03':'ı','CDM04':'i\u0307\u0301','CDM05':'tıtle','CDM06':'APPLİCATİON','CDM07':'fıle','CDM08':'i\u0307','CDM20':'hello','CDM21':'123-_'}
ASCII={'CDM01':'i','CDM02':'I','CDM03':'i','CDM04':'i\u0301','CDM05':'title','CDM06':'APPLICATION','CDM07':'file','CDM08':'İ','CDM20':'hello','CDM21':'123-_'}
COMPARE={
 'locale_collator':{'CDM09':False,'CDM10':True,'CDM11':False},
 'ordinal_ignore':{'CDM09':True,'CDM10':False,'CDM11':True},'unicode_fold':{'CDM09':True,'CDM10':False,'CDM11':True},
 'java_ignore':{'CDM09':True,'CDM10':True,'CDM11':True},'ascii_ignore':{'CDM09':True,'CDM10':False,'CDM11':True}}

def contract_expected(sc,mode):
 if sc['operation'] in {'lower','upper'}:
  if mode=='dotnet_locale':
   if sc['id']=='CDM04':return DEFAULT[sc['id']]
   if sc['id']=='CDM08':return 'İ'
   return TAILORED[sc['id']] if sc['locale']!='root' else DEFAULT[sc['id']]
  if mode=='dotnet_invariant':return 'İ' if sc['id']=='CDM08' else DEFAULT[sc['id']]
  if mode in {'locale_full'}:return TAILORED[sc['id']] if sc['locale']!='root' else DEFAULT[sc['id']]
  if mode in {'turkic_simple','turkic_full'}:return TAILORED[sc['id']]
  if mode=='go_simple':return 'i' if sc['id']=='CDM08' else DEFAULT[sc['id']]
  if mode=='ascii':return ASCII[sc['id']]
  return DEFAULT[sc['id']]
 return COMPARE[mode][sc['id']]

def app_expected(sc):return sc['application_expected']
def base_row(sc,eco,var,api_class,gran,backend,locale_requested):
 return {'observation_id':'','case_id':sc['id'],'case_layer':'application_scenario','scenario_family':sc['family'],'text_domain':sc['text_domain'],'operation':sc['operation'],'ecosystem':eco,'runtime_version':VERS.get(eco,''),'api_id':var,'api_class':api_class,'mapping_granularity':gran,'backend_family':backend,'backend_version':VERS['icu'] if backend=='icu_direct_or_bundled' else VERS['libc'] if backend=='libc_glibc' else VERS.get(eco,''),'unicode_version':VERS.get('node_components',{}).get('unicode') if eco=='Node' else VERS['python_unidata'] if eco=='Python' else None,'cldr_version':VERS.get('node_components',{}).get('cldr') if eco=='Node' else None,'icu_version':VERS['icu'] if backend in {'icu_direct_or_bundled','dotnet_globalization'} else None,'libc_version':VERS['libc'] if backend=='libc_glibc' else None,'platform':platform.platform(),'locale_requested':locale_requested,'locale_effective':'','input_escaped':ESC(sc.get('input','')),'input_codepoints':CP(sc.get('input','')),'second_input_escaped':ESC(sc.get('input2','')),'second_input_codepoints':CP(sc.get('input2','')),'expected_standard':None,'expected_contract':None,'expected_application':app_expected(sc),'actual_escaped':None,'actual_codepoints':None,'actual_relation':None,'exit_code':None,'exception':'','stderr':'','duration_ms':None,'standards_oracle_status':'not_applicable','api_contract_status':'','application_oracle_status':'','final_outcome':''}

def finalize(row,res,cexp,sexpected=False):
 st=res.get('status');row.update({'locale_effective':res.get('effective_locale',''),'exit_code':res.get('exit_code'),'exception':res.get('error',''),'stderr':res.get('stderr',''),'duration_ms':res.get('duration_ms')})
 if st in {'unsupported','environment_unavailable'}:row['api_contract_status']=st;row['application_oracle_status']=st;row['final_outcome']=st;return row
 if st not in {'ok'} or res.get('exit_code')!=0:row['api_contract_status']='execution_error';row['application_oracle_status']='execution_error';row['final_outcome']='execution_error';return row
 actual=res.get('actual');row['expected_contract']=cexp
 if isinstance(actual,str):row['actual_escaped']=ESC(actual);row['actual_codepoints']=CP(actual)
 else:row['actual_relation']=actual
 row['api_contract_status']='conformant' if cexp=='locale_defined' or actual==cexp else 'nonconformant'
 if sexpected:row['expected_standard']=cexp;row['standards_oracle_status']='conformant' if actual==cexp else 'nonconformant'
 app=row['expected_application'];row['application_oracle_status']='correct' if actual==app else ('cdm_hazard' if row['api_contract_status']=='conformant' else 'implementation_nonconformance')
 row['final_outcome']='application_correct' if row['application_oracle_status']=='correct' else row['application_oracle_status'];return row

rows=[];counter=0
def add(row):
 global counter;counter+=1;row['observation_id']=f'OBS{counter:04d}';rows.append(row)

# Mapping and comparison cells.
for sc in SCENARIOS:
 if sc['operation'] not in {'lower','upper','compare_equal'}:continue
 for eco,var,ops,mode,aclass,gran,backend,std in VARIANTS:
  if sc['operation'] not in ops:continue
  row=base_row(sc,eco,var,aclass,gran,backend,sc['locale'])
  if eco=='Node' and var=='explicit_locale' and sc['locale']=='root':
   add(finalize(row,{'status':'unsupported','error':'ECMA-402_requires_a_structurally_valid_language_tag','exit_code':0},None));continue
  if var in {'turkic_special','turkic'} and not (sc['locale'].startswith('tr') or sc['locale'].startswith('az')):
   add(finalize(row,{'status':'unsupported','error':'tailoring_not_available','exit_code':0},None));continue
  loc='tr_TR.utf8' if eco=='Python' and var=='locale_collator' and sc['locale'].startswith('tr') else sc['locale']
  res=invoke(eco,var,sc['operation'],loc,sc['input'],sc.get('input2',''))
  cexp='locale_defined' if eco=='Python' and var=='locale_collator' else contract_expected(sc,mode)
  add(finalize(row,res,cexp,std))

# Normalization family including explicit unsupported standard-library cells.
for sc in SCENARIOS:
 if sc['operation'] not in {'normalize_compare','normalize_lower_compare'}:continue
 for eco,var,backend,std in NORMALIZERS:
  row=base_row(sc,eco,var,'unicode_defined' if eco not in {'Go','Rust'} else 'unsupported','not_applicable',backend,sc['locale'])
  res=invoke(eco,var,sc['operation'],sc['locale'],sc['input'],sc['input2'])
  add(finalize(row,res,True,std))

# Native/libc family: every call is an isolated adapter process; English and C are negative controls.
locale_conditions={'tr_TR.UTF-8':'tr_TR.utf8','en_US.UTF-8':'en_US.utf8','C.UTF-8':'C.utf8'}
for sc in SCENARIOS:
 if sc['family']!='F5_native_libc_contamination':continue
 for semantic,loc in locale_conditions.items():
  for var in ('libc_process','ascii'):
   row=base_row(sc,'C',var,'default_locale_sensitive' if var=='libc_process' else 'ordinal_canonical','simple_code_point','libc_glibc' if var=='libc_process' else 'runtime_unicode_tables',semantic)
   op=sc['operation'];res=invoke('C',var,op,loc,sc['input'],sc.get('input2',''))
   cexp='locale_defined' if var=='libc_process' else sc['application_expected']
   add(finalize(row,res,cexp,False))

# Persisted collation/provider signatures and pre-frozen cross-provider stability observations.
probe=next(s for s in SCENARIOS if s['id']=='CDM17')['probe_set'];signatures={};effective={};pair_inputs=list(combinations(probe,2))
for eco,var,loc,backend in COLLATION_PROVIDERS:
 sig=[];eff=''
 for x,y in pair_inputs:
  r=invoke(eco,var,'compare_relation',loc,x,y)
  if r.get('status')!='ok':sig=None;eff=r.get('effective_locale','');break
  sig.append(r['actual']);eff=r.get('effective_locale','')
 signatures[(eco,var,backend)]=sig;effective[(eco,var,backend)]=eff

sc18=next(s for s in SCENARIOS if s['id']=='CDM18')
for key,sig in signatures.items():
 eco,var,backend=key;second=[] if sig is not None else None
 if sig is not None:
  for x,y in pair_inputs:second.append(invoke(eco,var,'compare_relation',next(p[2] for p in COLLATION_PROVIDERS if p[0]==eco and p[1]==var),x,y)['actual'])
 row=base_row(sc18,eco,var,'explicit_or_process_locale_collation','not_applicable',backend,'tr-TR');row['locale_effective']=effective[key];row['expected_contract']=True;row['expected_application']=True;stable=sig is not None and sig==second;row['actual_relation']=stable;row['api_contract_status']='conformant' if stable else 'nonconformant';row['application_oracle_status']='correct' if stable else 'implementation_nonconformance';row['final_outcome']='application_correct' if stable else 'implementation_nonconformance';add(row)

sc17=next(s for s in SCENARIOS if s['id']=='CDM17');sc19=next(s for s in SCENARIOS if s['id']=='CDM19')
for ka,kb in combinations(signatures,2):
 for sc in (sc17,sc19):
  eco=f'{ka[0]}->{kb[0]}';api=f'{ka[1]}->{kb[1]}';backend=f'{ka[2]}->{kb[2]}';row=base_row(sc,eco,api,'cross_provider_no_stability_promise','not_applicable',backend,'tr-TR');row['runtime_version']=f'{VERS.get(ka[0],"")} -> {VERS.get(kb[0],"")}';row['locale_effective']=f'{effective[ka]} -> {effective[kb]}'
  if signatures[ka] is None or signatures[kb] is None:row['api_contract_status']='environment_unavailable';row['application_oracle_status']='environment_unavailable';row['final_outcome']='environment_unavailable';add(row);continue
  if sc['id']=='CDM17':actual=signatures[ka]==signatures[kb]
  else:
   idx=pair_inputs.index(('İ','İ'));actual=(signatures[ka][idx]==0)==(signatures[kb][idx]==0)
  row['expected_contract']='no_cross_provider_stability_promise';row['expected_application']=True;row['actual_relation']=actual;row['api_contract_status']='conformant';row['application_oracle_status']='correct' if actual else 'cdm_hazard';row['final_outcome']='application_correct' if actual else 'cdm_hazard';add(row)

rawdir=ROOT/'out/benchmark/raw';procdir=ROOT/'out/benchmark/processed';envdir=ROOT/'out/benchmark/environment';rawdir.mkdir(parents=True,exist_ok=True);procdir.mkdir(parents=True,exist_ok=True);envdir.mkdir(parents=True,exist_ok=True)
raw=rawdir/'controlled_observations.jsonl';raw.write_text(''.join(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n' for r in rows),encoding='utf-8')
fields=list(rows[0]);csvpath=procdir/'controlled_observations.csv'
with csvpath.open('w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
signature_file=rawdir/'collation_provider_signatures.json';signature_file.write_text(json.dumps({'probe_set':probe,'pair_order':pair_inputs,'signatures':{f'{k[0]}::{k[1]}::{k[2]}':v for k,v in signatures.items()},'effective_locales':{f'{k[0]}::{k[1]}::{k[2]}':v for k,v in effective.items()}},ensure_ascii=False,indent=2),encoding='utf-8')
summary={'generated_at_utc':datetime.now(timezone.utc).isoformat(),'n_controlled_observations':len(rows),'final_outcomes':dict(Counter(r['final_outcome'] for r in rows)),'api_contract_status':dict(Counter(r['api_contract_status'] for r in rows)),'standards_oracle_status':dict(Counter(r['standards_oracle_status'] for r in rows)),'by_ecosystem':{e:dict(Counter(r['final_outcome'] for r in rows if r['ecosystem']==e)) for e in sorted(set(r['ecosystem'] for r in rows))},'scenario_counts':dict(Counter(r['scenario_family'] for r in rows))}
(procdir/'controlled_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2,sort_keys=True),encoding='utf-8')
env={'captured_at_utc':datetime.now(timezone.utc).isoformat(),'platform':platform.platform(),'versions':VERS,'installed_locales':firstline(['locale','-a']),'installed_locales_full':subprocess.run(['locale','-a'],text=True,capture_output=True).stdout.split(),'commands':COMMANDS}
(envdir/'full_environment.json').write_text(json.dumps(env,ensure_ascii=False,indent=2,sort_keys=True),encoding='utf-8')
for p in (raw,csvpath,signature_file,procdir/'controlled_summary.json',envdir/'full_environment.json'):print(hashlib.sha256(p.read_bytes()).hexdigest(),p.relative_to(ROOT))
print(json.dumps(summary,ensure_ascii=False,indent=2))
