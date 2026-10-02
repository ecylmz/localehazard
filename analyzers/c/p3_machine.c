/* Role: machine text (configuration keyword); ASCII-only mapping. */
#include <stddef.h>
void config_key(char *keyword) { for (size_t i = 0; keyword[i] != '\0'; i++) if (keyword[i] >= 'A' && keyword[i] <= 'Z') keyword[i] = (char)(keyword[i] + ('a' - 'A')); }
