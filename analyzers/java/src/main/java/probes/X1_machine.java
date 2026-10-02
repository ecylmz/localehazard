package probes;
import java.util.Locale;
import java.util.Map;
/** Context: the result is used as a key of a header map. */
public final class X1_machine {
    private static final Locale TR = Locale.forLanguageTag("tr-TR");
    public static void addHeader(Map<String, String> headers, String name, String value) {
        headers.put(name.toLowerCase(TR), value);
    }
}
