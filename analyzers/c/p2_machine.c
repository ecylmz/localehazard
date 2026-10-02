/* Role: machine text (configuration keyword). */
#include <locale.h>
#include <stddef.h>
#include <wctype.h>
void config_key(wchar_t *keyword) { locale_t tr = newlocale(LC_CTYPE_MASK, "tr_TR.UTF-8", (locale_t)0); if (!tr) return; for (size_t i = 0; keyword[i] != L'\0'; i++) keyword[i] = (wchar_t)towlower_l((wint_t)keyword[i], tr); freelocale(tr); }
