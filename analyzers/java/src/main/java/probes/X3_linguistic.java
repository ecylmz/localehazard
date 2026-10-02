package probes;
import java.text.Collator;
import java.util.List;
import javax.swing.DefaultListModel;
/** Context: names are sorted with the default collator and shown in a Swing list. */
public final class X3_linguistic {
    public static void show(DefaultListModel<String> model, List<String> names) {
        names.sort(Collator.getInstance());
        model.clear();
        names.forEach(model::addElement);
    }
}
