using System;
namespace Probes;
/// Role: machine text (protocol keyword match).
public static class P4_machine { public static bool IsKeyword(string token, string keyword) => string.Equals(token, keyword, StringComparison.CurrentCultureIgnoreCase); }
