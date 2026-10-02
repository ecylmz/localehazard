/* Role: linguistic text (names sorted for display to the user). */
#include <stdlib.h>
#include <string.h>
static int cmp(const void *a, const void *b) { return strcoll(*(const char *const *)a, *(const char *const *)b); }
void sort_for_display(const char **names, size_t n) { qsort((void *)names, n, sizeof *names, cmp); }
