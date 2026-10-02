/* LD_PRELOAD shim: report the glibc release whose locale data are in LOCPATH,
   so PostgreSQL records the collation version an unmodified 2.27 host would record. */
#include <stdlib.h>
const char *gnu_get_libc_version(void) { const char *v = getenv("SHIM_LIBC_VERSION"); return v ? v : "2.27"; }
