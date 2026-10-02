using System.Collections.Generic;
using System.Globalization;
namespace Probes;
/// Context: the result is used as a key of a header dictionary.
public static class X1_machine { static readonly CultureInfo Tr = new("tr-TR"); public static void AddHeader(Dictionary<string, string> headers, string name, string value) => headers[name.ToLower(Tr)] = value; }
