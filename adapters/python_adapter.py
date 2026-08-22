import base64,json,locale,sys,unicodedata
v,op,loc,a,*rest=sys.argv[1:];d=lambda x:base64.b64decode(x).decode();b=lambda x:base64.b64encode(x.encode()).decode();x=d(a);y=d(rest[0]) if rest else ''
def out(**kw): print(json.dumps(kw,ensure_ascii=True),end='')
if v=='normalizer':
 n1,n2=unicodedata.normalize('NFC',x),unicodedata.normalize('NFC',y)
 if op=='normalize_lower_compare':n1,n2=n1.lower(),n2.lower()
 out(status='ok',kind='bool',value=n1==n2,effective_locale='root')
elif v=='locale_collator':
 try: eff=locale.setlocale(locale.LC_ALL,loc)
 except locale.Error: out(status='environment_unavailable',error='setlocale_failed',effective_locale='')
 else:
  r=locale.strcoll(x,y);out(status='ok',kind='int' if op=='compare_relation' else 'bool',value=(-1 if r<0 else 1 if r>0 else 0) if op=='compare_relation' else r==0,effective_locale=eff)
elif v=='casefold':
 if op=='fold':out(status='ok',kind='string',value_b64=b(x.casefold()),effective_locale='root')
 else:out(status='ok',kind='bool',value=x.casefold()==y.casefold(),effective_locale='root')
else:
 r=x.lower() if op=='lower' else x.upper();out(status='ok',kind='string',value_b64=b(r),effective_locale='root')
