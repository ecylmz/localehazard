package probes;
/** Context: the result is matched against ASCII command literals. */
public final class X2_machine {
    public static int dispatch(String command) {
        switch (command.toLowerCase()) {
            case "file": return 1;
            case "title": return 2;
            default: return 0;
        }
    }
}
