package probes;
import java.text.Collator;
import java.util.List;
/** Role: machine text (keys written to a sorted index later searched with String.compareTo). */
public final class P5_machine {
    public static void sortIndexKeys(List<String> keys) {
        keys.sort(Collator.getInstance());
    }
}
