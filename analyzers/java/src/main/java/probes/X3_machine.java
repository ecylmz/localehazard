package probes;
import java.text.Collator;
import java.util.Collections;
import java.util.List;
/** Context: keys are sorted with the default collator and then binary-searched in natural (UTF-16) order. */
public final class X3_machine {
    public static int find(List<String> keys, String key) {
        keys.sort(Collator.getInstance());
        return Collections.binarySearch(keys, key);
    }
}
