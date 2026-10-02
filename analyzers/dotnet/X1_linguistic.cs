using System;
using System.Globalization;
namespace Probes;
/// Context: the result is written to the user's console.
public static class X1_linguistic { static readonly CultureInfo Tr = new("tr-TR"); public static void Show(string userText) => Console.WriteLine(userText.ToLower(Tr)); }
