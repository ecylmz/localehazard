package probes;
import java.text.Collator;
/** Role: machine text (protocol keyword match). */
public final class P4_machine {
    public static boolean isKeyword(String token, String keyword) {
        Collator c = Collator.getInstance();
        c.setStrength(Collator.SECONDARY);
        return c.equals(token, keyword);
    }
}
