#!/usr/bin/env bash
set -euo pipefail
study_dir="$(cd "$(dirname "$0")/.." && pwd)"
build_dir="$study_dir/build"
mkdir -p "$build_dir/java" "$build_dir/dotnet"
gcc -std=gnu17 -O2 -Wall -Wextra "$study_dir/adapters/CAdapter.c" -o "$build_dir/c_adapter" $(pkg-config --cflags --libs icu-uc icu-i18n)
javac -encoding UTF-8 -d "$build_dir/java" "$study_dir/adapters/JavaAdapter.java"
go build -trimpath -o "$build_dir/go_adapter" "$study_dir/adapters/go_adapter.go"
rustc -O "$study_dir/adapters/rust_adapter.rs" -o "$build_dir/rust_adapter"
dotnet build "$study_dir/adapters/dotnet/DotnetAdapter.csproj" -c Release -o "$build_dir/dotnet" --artifacts-path "$build_dir/dotnet_artifacts" --nologo
