package probes;
import java.text.Collator;
/** Role: linguistic text (user search term against a Turkish name). */
public final class P4_linguistic {
    public static boolean matchesName(String query, String name) {
        Collator c = Collator.getInstance();
        c.setStrength(Collator.SECONDARY);
        return c.equals(query, name);
    }
}
