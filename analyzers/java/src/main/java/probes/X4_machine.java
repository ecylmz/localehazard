package probes;
import java.util.Locale;
import java.util.Map;
/** Context: the result is used as a key of a header map. */
public final class X4_machine {
    public static void addHeader(Map<String, String> headers, String name, String value) {
        headers.put(name.toUpperCase(Locale.ROOT), value);
    }
}
