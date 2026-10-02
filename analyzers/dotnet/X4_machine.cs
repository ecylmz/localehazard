using System.Collections.Generic;
namespace Probes;
/// Context: the result is used as a key of a header dictionary.
public static class X4_machine { public static void AddHeader(Dictionary<string, string> headers, string name, string value) => headers[name.ToUpperInvariant()] = value; }
