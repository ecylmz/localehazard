// Usage: Runner <analyzer_dir> <rules,comma,separated> <side_dir>...
// For each side directory, compiles its *.cs files (with errors allowed) against the framework reference assemblies
// and prints one JSON line per analyzer diagnostic of the given rules: {"dir","file","line","rule"}.
using System.Collections.Immutable;
using System.Reflection;
using System.Text.Json;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.Diagnostics;

var analyzerDir = args[0];
var rules = args[1].Split(',').ToHashSet();
var loader = new Loader();
var analyzers = new[] { "Microsoft.CodeAnalysis.NetAnalyzers.dll", "Microsoft.CodeAnalysis.CSharp.NetAnalyzers.dll" }
    .SelectMany(f => new AnalyzerFileReference(Path.Combine(analyzerDir, f), loader).GetAnalyzers(LanguageNames.CSharp))
    .Where(a => a.SupportedDiagnostics.Any(d => rules.Contains(d.Id))).ToImmutableArray();
var refs = ((string)AppContext.GetData("TRUSTED_PLATFORM_ASSEMBLIES")!).Split(Path.PathSeparator)
    .Where(p => Path.GetFileName(p).StartsWith("System.") || Path.GetFileName(p) is "mscorlib.dll" or "netstandard.dll")
    .Select(p => (MetadataReference)MetadataReference.CreateFromFile(p)).ToList();
var parse = new CSharpParseOptions(LanguageVersion.Preview);
const string globalUsings = "global using System; global using System.Collections.Generic; global using System.IO; global using System.Linq; global using System.Net.Http; global using System.Threading; global using System.Threading.Tasks;";
var options = new CSharpCompilationOptions(OutputKind.DynamicallyLinkedLibrary)
    .WithSpecificDiagnosticOptions(rules.ToDictionary(r => r, _ => ReportDiagnostic.Warn));
Console.Error.WriteLine($"analyzers {analyzers.Length}, roslyn {typeof(Compilation).Assembly.GetName().Version}");
foreach (var dir in args.Skip(2))
{
    var trees = Directory.EnumerateFiles(dir, "*.cs", SearchOption.AllDirectories)
        .Select(f => CSharpSyntaxTree.ParseText(File.ReadAllText(f), parse, f)).ToList();
    trees.Add(CSharpSyntaxTree.ParseText(globalUsings, parse, "__GlobalUsings.cs"));
    var comp = CSharpCompilation.Create("C", trees, refs, options);
    var diags = await comp.WithAnalyzers(analyzers).GetAnalyzerDiagnosticsAsync();
    foreach (var d in diags.Where(d => rules.Contains(d.Id) && d.Location.IsInSource))
    {
        var span = d.Location.GetLineSpan();
        Console.WriteLine(JsonSerializer.Serialize(new { dir, file = Path.GetRelativePath(dir, span.Path), line = span.StartLinePosition.Line + 1, rule = d.Id }));
    }
}

class Loader : IAnalyzerAssemblyLoader
{
    public void AddDependencyLocation(string fullPath) { }
    public Assembly LoadFromPath(string fullPath) => Assembly.LoadFrom(fullPath);
}
