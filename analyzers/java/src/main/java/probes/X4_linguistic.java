package probes;
import java.util.Locale;
import javax.swing.JLabel;
/** Context: Turkish user text is shown in upper case in a Swing label. */
public final class X4_linguistic {
    public static void show(JLabel label, String userText) {
        label.setText(userText.toUpperCase(Locale.ROOT));
    }
}
