import probes.*;
import java.util.*;
public class Harness {
  static void out(String p, String role, boolean ok){ System.out.println("java\t"+p+"\t"+role+"\t"+(ok?"CORRECT":"CDM")); }
  public static void main(String[] a){
    List<String> keys = new ArrayList<>(List.of("cam","çay","dağ","Zeta","alpha","İzmir","ırmak","ilk"));
    List<String> bytewise = new ArrayList<>(keys); Collections.sort(bytewise);
    out("P1","machine", P1_machine.headerKey("TITLE").equals("title"));
    out("P1","linguistic", P1_linguistic.displayLower("IŞIK").equals("ışık"));
    out("P2","machine", P2_machine.configKey("TITLE").equals("title"));
    out("P2","linguistic", P2_linguistic.displayLower("IŞIK").equals("ışık"));
    out("P3","machine", P3_machine.configKey("TITLE").equals("title"));
    out("P3","linguistic", P3_linguistic.displayLower("IŞIK").equals("ışık"));
    out("P4","machine", P4_machine.isKeyword("FILE","file"));
    out("P4","linguistic", P4_linguistic.matchesName("IŞIK","ışık") && !P4_linguistic.matchesName("ISIK","ışık"));
    List<String> k1=new ArrayList<>(keys); P5_machine.sortIndexKeys(k1); out("P5","machine", k1.equals(bytewise));
    List<String> k2=new ArrayList<>(List.of("dağ","çay","cam")); P5_linguistic.sortForDisplay(k2); out("P5","linguistic", k2.equals(List.of("cam","çay","dağ")));
  }
}
