"""Round-4 RQ2 real-code evaluation, .NET analyzers (exploratory, post hoc; protocol/DEVIATIONS.md, 2026-11-13).

Usage: python3 src/r4_rq2_run_dotnet.py <realcode_dir> <out_dir>
Runs the .NET SDK analyzers of RQ2 (CA1304, CA1305, CA1307, CA1308, CA1309, CA1310, CA1311, CA1862, all set to
warning) on the C# files fetched by src/r4_rq2_fetch_files.py. The files of one lineage side
(<realcode_dir>/<sha>/<pre|post>/) form one compilation against the framework reference assemblies. The files do not
compile outside their repositories, so src/r4_rq2_dotnet_runner/ runs the analyzers through the compiler API on a
compilation with errors; a call whose receiver type does not resolve cannot be flagged. Writes <out_dir>/dotnet.json
in the layout of PMD's JSON report (paths /src/<sha>/<side>/<file>) and <out_dir>/dotnet_version.txt.
"""
import json, os, pathlib, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = pathlib.Path(sys.argv[1]).resolve()
OUT = pathlib.Path(sys.argv[2]).resolve(); OUT.mkdir(parents=True, exist_ok=True)
RULES = ["CA1304", "CA1305", "CA1307", "CA1308", "CA1309", "CA1310", "CA1311", "CA1862"]
env = dict(os.environ, DOTNET_CLI_TELEMETRY_OPTOUT="1", DOTNET_NOLOGO="1")
sdk = subprocess.run(["dotnet", "--version"], capture_output=True, text=True, env=env, check=True).stdout.strip()
root = pathlib.Path(subprocess.run(["dotnet", "--list-sdks"], capture_output=True, text=True, env=env, check=True)
                    .stdout.split(f"{sdk} [")[1].split("]")[0])
analyzers = root / sdk / "Sdks/Microsoft.NET.Sdk/analyzers"
binp = OUT / "runner_bin"
subprocess.run(["dotnet", "build", str(ROOT / "src/r4_rq2_dotnet_runner/Runner.csproj"), "-c", "Release", "-o", str(binp),
                "-nologo", "-v", "q"], env=env, check=True, capture_output=True)
sides = sorted(str(d) for d in SRC.glob("*/*") if d.is_dir() and any(d.rglob("*.cs")))
r = subprocess.run(["dotnet", str(binp / "Runner.dll"), str(analyzers), ",".join(RULES), *sides],
                   capture_output=True, text=True, env=env, check=True)
files = {}
for d in sides:
    p = pathlib.Path(d)
    for f in p.rglob("*.cs"):
        files[f"/src/{p.parent.name}/{p.name}/{f.relative_to(p).as_posix()}"] = []
for line in r.stdout.splitlines():
    e = json.loads(line); p = pathlib.Path(e["dir"])
    files.setdefault(f"/src/{p.parent.name}/{p.name}/{pathlib.PurePath(e['file']).as_posix()}", []).append(
        {"rule": e["rule"], "beginline": e["line"]})
json.dump({"files": [{"filename": k, "violations": v} for k, v in sorted(files.items())]}, open(OUT / "dotnet.json", "w"), indent=1)
(OUT / "dotnet_version.txt").write_text(f"dotnet sdk {sdk}\n{r.stderr.strip()}\nrules {' '.join(RULES)}\nsides {len(sides)}\n")
print(f"sides {len(sides)}, findings {sum(len(v) for v in files.values())}")
