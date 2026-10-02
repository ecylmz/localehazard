package probes;
import java.util.Locale;
import javax.swing.JLabel;
/** Context: the result is shown to the user in a Swing label. */
public final class X1_linguistic {
    private static final Locale TR = Locale.forLanguageTag("tr-TR");
    public static void show(JLabel label, String userText) {
        label.setText(userText.toLowerCase(TR));
    }
}
