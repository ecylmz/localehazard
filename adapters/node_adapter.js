const d=x=>Buffer.from(x,'base64').toString('utf8'), b=x=>Buffer.from(x,'utf8').toString('base64');
const [v,op,loc,a,z='']=process.argv.slice(2),x=d(a),y=z?d(z):'';const out=o=>process.stdout.write(JSON.stringify(o));
if(v==='normalizer'){let n1=x.normalize('NFC'),n2=y.normalize('NFC');if(op==='normalize_lower_compare'){n1=n1.toLowerCase();n2=n2.toLowerCase()}out({status:'ok',kind:'bool',value:n1===n2,effective_locale:'root'});}
else if(v==='collator'){const c=new Intl.Collator(loc,{sensitivity:'base',usage:'search'}),r=Math.sign(c.compare(x,y));out({status:'ok',kind:op==='compare_relation'?'int':'bool',value:op==='compare_relation'?r:r===0,effective_locale:c.resolvedOptions().locale});}
else {const r=v==='explicit_locale'?(op==='lower'?x.toLocaleLowerCase(loc):x.toLocaleUpperCase(loc)):(op==='lower'?x.toLowerCase():x.toUpperCase());out({status:'ok',kind:'string',value_b64:b(r),effective_locale:v==='explicit_locale'?loc:'root'});}
