import * as p1m from './p1_machine.js'; import * as p1l from './p1_linguistic.js';
const mach = [['TITLE','title'],['FILE','file'],['ID','id']];
const ling = [['IŞIK','ışık'],['KIRMIZI','kırmızı'],['IRMAK','ırmak'],['ÇIRA','çıra']];
for (const [i,e] of mach) console.log(JSON.stringify({role:'machine', input:i, out:p1m.headerKey(i), ok:p1m.headerKey(i)===e}));
for (const [i,e] of ling) console.log(JSON.stringify({role:'linguistic', input:i, out:p1l.displayLower(i), ok:p1l.displayLower(i)===e}));
console.log(JSON.stringify({upper:'istanbul'.toLocaleUpperCase(), expectedTr:'İSTANBUL'}));
