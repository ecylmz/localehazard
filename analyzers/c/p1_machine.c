/* Role: machine text (HTTP header name used as a hash key); process locale set by setlocale(LC_ALL, ""). */
#include <ctype.h>
#include <stddef.h>
void header_key(char *header_name) { for (size_t i = 0; header_name[i] != '\0'; i++) header_name[i] = (char)tolower((unsigned char)header_name[i]); }
