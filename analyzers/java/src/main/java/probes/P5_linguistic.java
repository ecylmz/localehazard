package probes;
import java.text.Collator;
import java.util.List;
/** Role: linguistic text (names sorted for display to a Turkish user). */
public final class P5_linguistic {
    public static void sortForDisplay(List<String> names) {
        names.sort(Collator.getInstance());
    }
}
