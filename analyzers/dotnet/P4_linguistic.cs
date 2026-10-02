using System;
namespace Probes;
/// Role: linguistic text (user search term against a Turkish name).
public static class P4_linguistic { public static bool MatchesName(string query, string name) => string.Equals(query, name, StringComparison.CurrentCultureIgnoreCase); }
