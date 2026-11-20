#!/bin/sh
# Round-4 RQ3 check: which libc collations does PostgreSQL 18.6 version-track? (protocol/DEVIATIONS.md, 2026-11-09)
# PostgreSQL records no collation version for libc locales named C, C.* or POSIX (get_collation_actual_version_libc),
# so a change of C.UTF-8 sort order (Debian/Ubuntu shipped a patched C.UTF-8 before glibc 2.35) is never reported.
# The builtin provider's C.UTF-8 (collation bu) is versioned by PostgreSQL itself and is listed for comparison.
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
export LD_LIBRARY_PATH="$HERE/pg/lib"
# en_US.UTF-8 is compiled by build_env.sh into dbms/loc/new; use it when the host has no en_US locale.
locale -a 2>/dev/null | grep -qi "^en_US.utf-\{0,1\}8$" || export LOCPATH="$HERE/loc/new"
D=$(mktemp -d)
trap '"$HERE/pg/bin/pg_ctl" -D "$D/data" -w stop >/dev/null 2>&1 || true; rm -rf "$D"' EXIT
"$HERE/pg/bin/initdb" -D "$D/data" -U postgres --locale=C.UTF-8 --encoding=UTF8 --no-instructions >/dev/null 2>&1
"$HERE/pg/bin/pg_ctl" -D "$D/data" -o "-p 55498 -k $D -c listen_addresses=" -l "$D/log" -w start >/dev/null
q() { "$HERE/pg/bin/psql" -X -p 55498 -h "$D" -U postgres -d postgres -At -c "$1"; }
echo "server: $(q "SELECT version()")"
echo "glibc: $(ldd --version | head -1)"
echo "database C.UTF-8 datcollversion: $(q "SELECT quote_nullable(datcollversion) FROM pg_database WHERE datname=current_database()")"
q "CREATE COLLATION cu (provider=libc, locale='C.UTF-8')" >/dev/null
q "CREATE COLLATION eu (provider=libc, locale='en_US.UTF-8')" >/dev/null
q "CREATE COLLATION bu (provider=builtin, locale='C.UTF-8')" >/dev/null
q "SELECT collname || ': collversion=' || quote_nullable(collversion) || ', actual=' || quote_nullable(pg_collation_actual_version(oid)) FROM pg_collation WHERE collname IN ('bu','cu','eu') ORDER BY 1"
