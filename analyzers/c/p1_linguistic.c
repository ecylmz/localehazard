/* Role: linguistic text (user-visible name in the user's locale); process locale set by setlocale(LC_ALL, ""). */
#include <ctype.h>
#include <stddef.h>
void display_lower(char *user_text) { for (size_t i = 0; user_text[i] != '\0'; i++) user_text[i] = (char)tolower((unsigned char)user_text[i]); }
