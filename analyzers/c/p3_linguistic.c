/* Role: linguistic text (Turkish user text); ASCII-only mapping. */
#include <stddef.h>
void display_lower(char *user_text) { for (size_t i = 0; user_text[i] != '\0'; i++) if (user_text[i] >= 'A' && user_text[i] <= 'Z') user_text[i] = (char)(user_text[i] + ('a' - 'A')); }
