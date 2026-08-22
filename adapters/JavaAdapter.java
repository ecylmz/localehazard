import java.nio.charset.StandardCharsets;import java.text.Collator;import java.text.Normalizer;import java.util.*;
public class JavaAdapter{
 static String d(String x){return new String(Base64.getDecoder().decode(x),StandardCharsets.UTF_8);}static String b(String x){return Base64.getEncoder().encodeToString(x.getBytes(StandardCharsets.UTF_8));}
 static void s(String v,String l){System.out.print("{\"status\":\"ok\",\"kind\":\"string\",\"value_b64\":\""+b(v)+"\",\"effective_locale\":\""+l+"\"}");}static void q(boolean v,String l){System.out.print("{\"status\":\"ok\",\"kind\":\"bool\",\"value\":"+v+",\"effective_locale\":\""+l+"\"}");}static void n(int v,String l){System.out.print("{\"status\":\"ok\",\"kind\":\"int\",\"value\":"+Integer.signum(v)+",\"effective_locale\":\""+l+"\"}");}
 public static void main(String[]a){String v=a[0],op=a[1],tag=a[2],x=d(a[3]),y=a.length>4?d(a[4]):"";Locale l=tag.equals("root")?Locale.ROOT:Locale.forLanguageTag(tag);
  if(v.equals("normalizer")){String n1=Normalizer.normalize(x,Normalizer.Form.NFC),n2=Normalizer.normalize(y,Normalizer.Form.NFC);if(op.equals("normalize_lower_compare")){n1=n1.toLowerCase(Locale.ROOT);n2=n2.toLowerCase(Locale.ROOT);}q(n1.equals(n2),"root");return;}
  if(v.equals("collator")){Collator c=Collator.getInstance(l);c.setStrength(Collator.PRIMARY);c.setDecomposition(Collator.CANONICAL_DECOMPOSITION);int r=c.compare(x,y);if(op.equals("compare_relation"))n(r,l.toLanguageTag());else q(r==0,l.toLanguageTag());return;}
  if(v.equals("equals_ignore_case")){q(x.equalsIgnoreCase(y),"root");return;}
  String r; if(v.equals("explicit_locale"))r=op.equals("lower")?x.toLowerCase(l):x.toUpperCase(l);else if(v.equals("root"))r=op.equals("lower")?x.toLowerCase(Locale.ROOT):x.toUpperCase(Locale.ROOT);else{Locale old=Locale.getDefault();Locale.setDefault(l);try{r=op.equals("lower")?x.toLowerCase():x.toUpperCase();}finally{Locale.setDefault(old);}}s(r,v.equals("root")?"root":l.toLanguageTag());
 }}
