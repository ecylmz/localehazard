#!/bin/sh
# Build the environment of the PostgreSQL collation-data experiment (manuscript RQ3) from pinned sources.
# Tested on Ubuntu 26.04 (glibc 2.43), x86_64 and arm64. Needs: a C toolchain, make, bison, flex, pkg-config,
# ICU development files, Python 3, curl, xz, bzip2, and the `locales` package (host locale sources).
# On Ubuntu: apt-get install build-essential bison flex pkg-config libicu-dev python3 curl xz-utils bzip2 locales wamerican
#
# Usage: sh dbms/build_env.sh [--bionic]
#   --bionic  also prepares the real glibc 2.27 runtime for dbms/emulation_check.py (x86_64 only): the Ubuntu 18.04
#             base image is extracted to dbms/bionic, and its own localedef compiles the glibc 2.27 en_US source into
#             dbms/loc/bionic (this reproduces the authors' loc/bionic bit for bit).
# Then run: python3 dbms/run_dbms_experiment.py synthetic && python3 dbms/run_dbms_experiment.py dictionary
# (as a non-root user; PostgreSQL refuses to run as root). The dictionary dataset is /usr/share/dict/american-english
# from the wamerican package; its SHA-256 is checked against the one in dbms/results/dbms_results_dictionary.json.
set -eu
H=$(cd "$(dirname "$0")" && pwd)
S="$H/src"; mkdir -p "$S" "$H/loc/old" "$H/loc/v228" "$H/loc/new"

fetch() {  # url sha256 file
  [ -f "$S/$3" ] || curl -fsSL -o "$S/$3" "$1"
  echo "$2  $S/$3" | sha256sum -c -
}
fetch https://ftp.postgresql.org/pub/source/v18.6/postgresql-18.6.tar.bz2 555610c24d53e4316da5b7d3fc25c279d96856d5e0e23ee308c328c5fa881d9f postgresql-18.6.tar.bz2
fetch https://ftp.gnu.org/gnu/glibc/glibc-2.27.tar.xz 5172de54318ec0b7f2735e5a91d908afe1c9ca291fec16b5374d9faadfc1fc72 glibc-2.27.tar.xz
fetch https://ftp.gnu.org/gnu/glibc/glibc-2.28.tar.xz b1900051afad76f7a4f73e71413df4826dce085ef8ddb785a945b66d7d513082 glibc-2.28.tar.xz

cd "$S"
[ -d postgresql-18.6 ] || tar xjf postgresql-18.6.tar.bz2
[ -d glibc-2.27/localedata ] || tar xJf glibc-2.27.tar.xz glibc-2.27/localedata
[ -d glibc-2.28/localedata ] || tar xJf glibc-2.28.tar.xz glibc-2.28/localedata
if [ ! -x "$H/pg/bin/postgres" ]; then
  cd postgresql-18.6
  ./configure --prefix="$H/pg" --with-icu --without-readline --without-zlib > "$S/configure.log"
  make -j"$(nproc)" > "$S/make.log" && make install > "$S/install.log"
  make -C contrib/amcheck install >> "$S/install.log" && make -C contrib/citext install >> "$S/install.log"
  cd "$S"
fi

for L in en_US tr_TR; do
  I18NPATH="$S/glibc-2.27/localedata" localedef -c -i "$L" -f UTF-8 "$H/loc/old/$L.UTF-8" || true
  I18NPATH="$S/glibc-2.28/localedata" localedef -c -i "$L" -f UTF-8 "$H/loc/v228/$L.UTF-8" || true
  localedef -c -i "$L" -f UTF-8 "$H/loc/new/$L.UTF-8" || true
done
gcc -shared -fPIC -o "$H/libcver_shim.so" "$H/libcver_shim.c"

if [ "${1:-}" = "--bionic" ]; then
  fetch https://cdimage.ubuntu.com/ubuntu-base/releases/18.04/release/ubuntu-base-18.04.5-base-amd64.tar.gz \
    8ff20b47bb123e4271da81b77ee56e6b5aeb85eaf7d9b1b5f6f3fbc7f11d07ea ubuntu-base-18.04.5-base-amd64.tar.gz
  B="$H/bionic"; mkdir -p "$B" "$H/loc/bionic"
  [ -x "$B/usr/bin/localedef" ] || tar xzf "$S/ubuntu-base-18.04.5-base-amd64.tar.gz" -C "$B" --exclude=dev/*
  I18NPATH="$S/glibc-2.27/localedata" "$B/lib/x86_64-linux-gnu/ld-2.27.so" \
    --library-path "$B/lib/x86_64-linux-gnu:$B/usr/lib/x86_64-linux-gnu" "$B/usr/bin/localedef" -c -i en_US -f UTF-8 "$H/loc/bionic/en_US.UTF-8" || true
fi
"$H/pg/bin/postgres" --version
ldd --version | head -1
ls "$H/loc"/*
