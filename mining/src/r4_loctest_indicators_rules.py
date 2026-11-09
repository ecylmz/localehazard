"""Locale-test expression shared by the round-4 scripts; identical to LOCTEST in src/post_review_rq3.py (section 4)."""
import re

LOCTEST = re.compile(r"(?i:tr[-_]TR|\"tr\"|'tr'|Locale\.setDefault|new Locale\(\s*\"tr|forLanguageTag\(\s*\"tr|CultureInfo\(\s*\"tr|Turkish|Turkey|LC_ALL|LC_CTYPE|LANG=|dotless|az[-_]AZ|lt[-_]LT)|[\u0130\u0131\u015e\u015f\u011e\u011f]")
