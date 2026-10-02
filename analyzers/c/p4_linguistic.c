/* Role: linguistic text (user search term against a name); process locale set by setlocale(LC_ALL, ""). */
#include <strings.h>
int matches_name(const char *query, const char *name) { return strcasecmp(query, name) == 0; }
