package probes;
import java.util.Locale;
/** Role: machine text (configuration keyword). */
public final class P2_machine {
    private static final Locale TR = Locale.forLanguageTag("tr-TR");
    public static String configKey(String keyword) {
        return keyword.toLowerCase(TR);
    }
}
