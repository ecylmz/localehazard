namespace Probes;
/// Context: the result is matched against ASCII command literals.
public static class X2_machine { public static int Dispatch(string command) => command.ToLower() switch { "file" => 1, "title" => 2, _ => 0 }; }
