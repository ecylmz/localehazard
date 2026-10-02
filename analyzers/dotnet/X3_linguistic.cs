using System;
using System.Collections.Generic;
namespace Probes;
/// Context: names are sorted with the current culture and written to the console.
public static class X3_linguistic { public static void Show(List<string> names) { names.Sort(StringComparer.CurrentCulture); names.ForEach(Console.WriteLine); } }
