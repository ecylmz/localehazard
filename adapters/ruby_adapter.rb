require 'json';require 'base64';v,op,loc,a,z=ARGV;x=Base64.decode64(a).force_encoding(Encoding::UTF_8);y=z ? Base64.decode64(z).force_encoding(Encoding::UTF_8) : ''
if v=='normalizer';n1=x.unicode_normalize(:nfc);n2=y.unicode_normalize(:nfc);if op=='normalize_lower_compare';n1=n1.downcase;n2=n2.downcase;end;o={status:'ok',kind:'bool',value:n1==n2,effective_locale:'root'}
elsif v=='casecmp';o={status:'ok',kind:'bool',value:x.casecmp?(y),effective_locale:'root'}
elsif v=='fold';r=x.downcase(:fold);o={status:'ok',kind:'string',value_b64:Base64.strict_encode64(r),effective_locale:'root'}
else;opts=v=='turkic'?[:turkic]:(v=='ascii'?[:ascii]:[]);begin;r=op=='lower'?x.downcase(*opts):x.upcase(*opts);o={status:'ok',kind:'string',value_b64:Base64.strict_encode64(r),effective_locale:v=='turkic'?loc:'root'};rescue ArgumentError=>e;o={status:'unsupported',error:e.message,effective_locale:loc};end;end
print JSON.generate(o)
