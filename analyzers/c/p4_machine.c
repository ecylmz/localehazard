/* Role: machine text (protocol keyword match); process locale set by setlocale(LC_ALL, ""). */
#include <strings.h>
int is_keyword(const char *token, const char *keyword) { return strcasecmp(token, keyword) == 0; }
