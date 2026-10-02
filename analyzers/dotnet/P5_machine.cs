using System;
using System.Collections.Generic;
namespace Probes;
/// Role: machine text (keys written to a sorted index later searched ordinally).
public static class P5_machine { public static void SortIndexKeys(List<string> keys) => keys.Sort(StringComparer.CurrentCulture); }
