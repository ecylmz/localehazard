# Round-4 evidence search: can glibc sort order change without a change of the reported version?

Search date: 2026-11-09. Question from the internal pre-submission review: is there a real instance of the RQ3 silent-drift condition? The
manuscript emulates it and quotes the case "as would happen if a distribution patched locale data without changing
the library version".

## Result

No source found reports a distribution update that changed glibc locale collation data while keeping the same
glibc version string on the same distribution release. Guidance and incident reports describe major
upgrades (glibc 2.27 to 2.28, Debian 9 to 10, RHEL 7 to 8), where PostgreSQL 13 and later warn.

One real path produces the same effect as the silent-drift condition (order changes, no warning). A second
observation shows that one upstream version string can carry different locale data:

1. PostgreSQL does not version-track libc collations named C, C.* or POSIX. In PostgreSQL 18.6,
   `get_collation_actual_version_libc()` returns no version for them
   (`src/backend/utils/adt/pg_locale_libc.c`). `dbms/r4_collversion_c_utf8.sh` shows it on a running server:
   a database and a collation with locale C.UTF-8 record `collversion = NULL`, while en_US.UTF-8 records `2.43`.
   Debian and Ubuntu shipped a patched C.UTF-8 before glibc 2.35 added an upstream C.UTF-8. Its order
   differed across Debian 9, 10, 11 and Ubuntu 22.04. The source is Daniel Verite's tests in the
   pgsql-hackers thread "pg_collation.collversion for C.UTF-8" (April 2023, https://hackorum.dev/topics/47764).
   Thomas Munro in the same thread: Debian and other systems "have been sorting text in some other order".
   Daniel Verite: users upgrading to glibc 2.35 or later "will not be having the normal warning about the need to reindex".
2. The same upstream version string can carry different locale data on different distributions. In
   Schneider's fingerprints (https://github.com/ardentperf/glibc-unicode-sorting), Debian 10
   (glibc 2.28-10+deb10u4) and RHEL 8 (glibc 2.28-251.el8_10.40) both report 2.28 but have different C.UTF-8
   checksums (en and de identical). The differing locale is C.UTF-8, which PostgreSQL does not track (path 1),
   so this example does not show a version-tracked collation that changes under the same version string.

Context: a 2015 pgsql-hackers thread reports de_DE.UTF-8 order changing from CentOS 5.11 to 6.6 and back in
7.1 ("Issues with german locale on CentOS 5,6,7", https://hackorum.dev/topics/128133). These releases ship different glibc versions, so it is not a same-version case. It shows that
distribution-specific locale data changed order outside the upstream 2.28 event.

## Consequence for the paper

The silent-drift condition can stay as an emulation. The paper can frame it as any order change that the version
proxy does not see, and give the C.UTF-8 path as a real instance. The C.UTF-8 path needs no emulation: a
database created with libc C.UTF-8 on Debian 11 and upgraded to Debian 12 (glibc 2.36) gets no warning.
