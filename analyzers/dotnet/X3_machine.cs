using System;
using System.Collections.Generic;
namespace Probes;
/// Context: keys are sorted with the current culture and then binary-searched ordinally.
public static class X3_machine { public static int Find(List<string> keys, string key) { keys.Sort(StringComparer.CurrentCulture); return keys.BinarySearch(key, StringComparer.Ordinal); } }
