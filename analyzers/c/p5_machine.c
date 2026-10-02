/* Role: machine text (keys written to a sorted index later searched with strcmp). */
#include <stdlib.h>
#include <string.h>
static int cmp(const void *a, const void *b) { return strcoll(*(const char *const *)a, *(const char *const *)b); }
void sort_index_keys(const char **keys, size_t n) { qsort((void *)keys, n, sizeof *keys, cmp); }
