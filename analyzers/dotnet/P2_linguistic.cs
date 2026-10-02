using System.Globalization;
namespace Probes;
/// Role: linguistic text (Turkish user text).
public static class P2_linguistic { static readonly CultureInfo Tr = new("tr-TR"); public static string DisplayLower(string userText) => userText.ToLower(Tr); }
