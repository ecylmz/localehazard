/* Role: linguistic text (Turkish user text). */
#include <locale.h>
#include <stddef.h>
#include <wctype.h>
void display_lower(wchar_t *user_text) { locale_t tr = newlocale(LC_CTYPE_MASK, "tr_TR.UTF-8", (locale_t)0); if (!tr) return; for (size_t i = 0; user_text[i] != L'\0'; i++) user_text[i] = (wchar_t)towlower_l((wint_t)user_text[i], tr); freelocale(tr); }
