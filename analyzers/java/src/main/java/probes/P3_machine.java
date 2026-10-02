package probes;
import java.util.Locale;
/** Role: machine text (configuration keyword). */
public final class P3_machine {
    public static String configKey(String keyword) {
        return keyword.toLowerCase(Locale.ROOT);
    }
}
