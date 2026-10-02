package probes;
import java.util.Locale;
/** Role: linguistic text (Turkish user text). */
public final class P2_linguistic {
    private static final Locale TR = Locale.forLanguageTag("tr-TR");
    public static String displayLower(String userText) {
        return userText.toLowerCase(TR);
    }
}
