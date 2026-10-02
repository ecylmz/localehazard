package probes;
import javax.swing.JLabel;
/** Context: the result is shown to the user in a Swing label. */
public final class X2_linguistic {
    public static void show(JLabel label, String userText) {
        label.setText(userText.toLowerCase());
    }
}
