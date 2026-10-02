package probes;
/** Role: machine text (HTTP header name used as a map key). */
public final class P1_machine {
    public static String headerKey(String headerName) {
        return headerName.toLowerCase();
    }
}
