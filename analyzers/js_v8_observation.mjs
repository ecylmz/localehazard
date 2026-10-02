// Incidental observation: ECMA-402 String.prototype.toLocaleLowerCase() with no argument must use DefaultLocale().
const inputs = ['I', 'TITLE', 'Iç', 'IŞ', 'IŞIK', 'İ'];
const dflt = new Intl.Collator().resolvedOptions().locale;
for (const s of inputs) {
  const d = s.toLocaleLowerCase(), e = s.toLocaleLowerCase(dflt);
  console.log(JSON.stringify({ node: process.version, icu: process.versions.icu, default: dflt, input: s, noArg: d, explicitDefault: e, consistent: d === e }));
}
