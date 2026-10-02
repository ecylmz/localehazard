using System.Globalization;
namespace Probes;
/// Role: machine text (configuration keyword).
public static class P2_machine { static readonly CultureInfo Tr = new("tr-TR"); public static string ConfigKey(string keyword) => keyword.ToLower(Tr); }
