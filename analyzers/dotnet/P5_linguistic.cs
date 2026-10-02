using System;
using System.Collections.Generic;
namespace Probes;
/// Role: linguistic text (names sorted for display to a Turkish user).
public static class P5_linguistic { public static void SortForDisplay(List<string> names) => names.Sort(StringComparer.CurrentCulture); }
