"""Deterministic RQ3 diff classifier (frozen 2026-10-01, before classifier outputs were inspected).

A *repair edit* is a removed line R and an added line A in the same hunk such that R matches a
locale-sensitive pattern S and A matches the paired target pattern T while no longer matching S, and the
two lines are similar (difflib ratio >= 0.5). Directions:
  MACHINE_PINNING  : locale-sensitive -> locale-neutral/ordinal/invariant/ASCII (machine-text repair)
  LINGUISTIC_REPAIR: locale-neutral/ASCII -> explicitly locale-aware (linguistic-text repair)
Operation classes: CASE, COMPARE, COLLATION, CTYPE, ENV, FORMAT (FORMAT is recorded but out of scope).
"""
import difflib, gzip, hashlib, json, pathlib, re, sys, csv

ROOT = pathlib.Path(__file__).resolve().parents[1]
EXT = {
    "jvm": (".java", ".kt", ".kts", ".groovy", ".scala"),
    "dotnet": (".cs", ".vb", ".fs", ".cshtml", ".razor"),
    "js": (".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs", ".vue", ".svelte"),
    "c_cpp": (".c", ".h", ".cc", ".cpp", ".cxx", ".hpp", ".hh", ".m", ".mm", ".inl"),
    "python": (".py", ".pyx"),
    "go": (".go",), "rust": (".rs",), "php": (".php", ".inc"), "ruby": (".rb",),
    "shell_build": (".sh", ".bash", ".zsh", ".mk", ".cmake", ".yml", ".yaml", ".bat", ".ps1"),
    "sql": (".sql",),
}
BUILD_NAMES = ("makefile", "dockerfile", "jenkinsfile", "gnumakefile")

NEUTRAL_JAVA = r"(Locale\.(ROOT|ENGLISH|US|UK|CANADA)|java\.util\.Locale\.(ROOT|ENGLISH|US|UK)|Locale\.forLanguageTag\(\"(en|und|en-US)\"\)|new Locale\(\"en\"|LOCALE_ROOT|ROOT_LOCALE|Locale\(\"\"\))"
R = lambda p: re.compile(p)
RULES = [
    # (ecosystem, op, direction, sensitive S, target T)
    ("jvm", "CASE", "MACHINE_PINNING", R(r"\.to(Lower|Upper)Case\(\s*\)"), R(r"\.to(Lower|Upper)Case\(\s*" + NEUTRAL_JAVA)),
    ("jvm", "CASE", "MACHINE_PINNING", R(r"\.to(Lower|Upper)Case\(\s*\)"), R(r"\.(lowercase|uppercase)\(\s*\)|toRoot(Lower|Upper)Case|Ascii\.to(Lower|Upper)Case|(?i:ascii)\w*(Lower|Upper)")),
    ("jvm", "CASE", "MACHINE_PINNING", R(r"\.to(Lower|Upper)Case\(\s*(Locale\.getDefault\(\)|locale|Locale\.(forLanguageTag|TURKISH)|new Locale\(\"tr)"), R(r"\.to(Lower|Upper)Case\(\s*" + NEUTRAL_JAVA)),
    ("jvm", "CASE", "LINGUISTIC_REPAIR", R(r"\.to(Lower|Upper)Case\(\s*(" + NEUTRAL_JAVA + r"|\s*\))"), R(r"\.to(Lower|Upper)Case\(\s*(locale|userLocale|getLocale\(\)|\w+\.getLocale\(\)|Locale\.forLanguageTag\(\"(tr|az|lt))")),
    ("jvm", "COLLATION", "MACHINE_PINNING", R(r"Collator\.getInstance\(\s*\)"), R(r"Collator\.getInstance\(\s*" + NEUTRAL_JAVA)),
    ("jvm", "FORMAT", "MACHINE_PINNING", R(r"String\.format\(\s*\""), R(r"String\.format\(\s*" + NEUTRAL_JAVA)),
    ("dotnet", "CASE", "MACHINE_PINNING", R(r"\.To(Lower|Upper)\(\s*\)"), R(r"\.To(Lower|Upper)Invariant\(\s*\)|\.To(Lower|Upper)\(\s*(System\.Globalization\.)?CultureInfo\.InvariantCulture")),
    ("dotnet", "CASE", "MACHINE_PINNING", R(r"\.To(Lower|Upper)\(\s*(CultureInfo\.CurrentCulture|culture|new CultureInfo)"), R(r"\.To(Lower|Upper)Invariant\(\s*\)|CultureInfo\.InvariantCulture")),
    ("dotnet", "CASE", "LINGUISTIC_REPAIR", R(r"\.To(Lower|Upper)Invariant\(\s*\)"), R(r"\.To(Lower|Upper)\(\s*(CultureInfo\.CurrentCulture|culture|cultureInfo|\w*[Cc]ulture\w*)\s*\)")),
    ("dotnet", "COMPARE", "MACHINE_PINNING", R(r"StringComparison\.(CurrentCulture|InvariantCulture)(IgnoreCase)?"), R(r"StringComparison\.Ordinal(IgnoreCase)?")),
    ("dotnet", "COMPARE", "MACHINE_PINNING", R(r"StringComparer\.(CurrentCulture|InvariantCulture)(IgnoreCase)?"), R(r"StringComparer\.Ordinal(IgnoreCase)?")),
    ("dotnet", "COMPARE", "MACHINE_PINNING", R(r"\.(StartsWith|EndsWith|IndexOf|LastIndexOf|Compare|CompareTo)\((?![^)]*StringComparison)[^)]*\)"), R(r"StringComparison\.Ordinal(IgnoreCase)?|string\.CompareOrdinal|String\.CompareOrdinal")),
    ("dotnet", "COMPARE", "MACHINE_PINNING", R(r"(string|String)\.Compare\([^,]+,[^,]+,\s*true\s*\)"), R(r"StringComparison\.OrdinalIgnoreCase|StringComparer\.OrdinalIgnoreCase")),
    ("dotnet", "COMPARE", "MACHINE_PINNING", R(r"\.To(Lower|Upper)(Invariant)?\(\)\s*==|==\s*\w+\.To(Lower|Upper)(Invariant)?\(\)"), R(r"StringComparison\.OrdinalIgnoreCase|StringComparer\.OrdinalIgnoreCase")),
    ("dotnet", "FORMAT", "MACHINE_PINNING", R(r"\.(ToString|Parse|TryParse)\((?![^)]*Culture)"), R(r"CultureInfo\.InvariantCulture|NumberFormatInfo\.InvariantInfo")),
    ("js", "CASE", "MACHINE_PINNING", R(r"\.toLocale(Lower|Upper)Case\("), R(r"\.to(Lower|Upper)Case\(\s*\)")),
    ("js", "CASE", "LINGUISTIC_REPAIR", R(r"\.to(Lower|Upper)Case\(\s*\)"), R(r"\.toLocale(Lower|Upper)Case\(")),
    ("c_cpp", "CASE", "MACHINE_PINNING", R(r"(?<![\w.>])(tolower|toupper|towlower|towupper)\s*\("), R(r"(?i:ascii)\w*(lower|upper)|(lower|upper)\w*(?i:ascii)|av_to(lower|upper)|g_ascii_to(lower|upper)|(tolower|toupper)_l\s*\(|c_to(lower|upper)|ap_to(lower|upper)|apr_to(lower|upper)|Py_TO(LOWER|UPPER)|rb_tolower|ISC_TOLOWER")),
    ("c_cpp", "COMPARE", "MACHINE_PINNING", R(r"(?<![\w.>])(strcasecmp|strncasecmp|_stricmp|stricmp|_strnicmp|strnicmp|wcscasecmp|_wcsicmp)\s*\("), R(r"(?i:ascii)\w*cmp|g_ascii_strn?casecmp|(strcasecmp|strncasecmp)_l\s*\(|av_strn?casecmp|c_strn?casecmp|ap_cstr_casecmp|apr_cstr_casecmp|\w*_strn?casecmp|PyOS_strn?icmp|st_strn?casecmp")),
    ("c_cpp", "CTYPE", "MACHINE_PINNING", R(r"(?<![\w.>])is(alpha|alnum|digit|space|upper|lower|xdigit|punct|print|graph|cntrl)\s*\("), R(r"(?i:ascii)\w*is\w*|is\w*(?i:ascii)|g_ascii_is\w+|av_is\w+|is\w+_l\s*\(|c_is\w+|IS_ASCII|isascii|Py_IS\w+|rb_is\w+")),
    ("c_cpp", "COLLATION", "MACHINE_PINNING", R(r"(?<![\w.>])(strcoll|wcscoll|strxfrm)\s*\("), R(r"(?<![\w.>])(strcmp|wcscmp|memcmp)\s*\(")),
    ("c_cpp", "ENV", "MACHINE_PINNING", R(r"setlocale\(\s*LC_ALL\s*,\s*\"\"\s*\)"), R(r"setlocale\(\s*LC_(CTYPE|MESSAGES|COLLATE|NUMERIC|TIME|MONETARY)\s*,|setlocale\(\s*LC_ALL\s*,\s*\"C")),
    ("python", "COLLATION", "MACHINE_PINNING", R(r"locale\.(strcoll|strxfrm)"), R(r"sorted\(|\.sort\(|==")),
    ("python", "CASE", "MACHINE_PINNING", R(r"string\.(lower|upper|lowercase|uppercase|letters)\b|locale\.setlocale\(\s*locale\.LC_ALL"), R(r"\.(lower|upper)\(\)|string\.ascii_\w+|locale\.setlocale\(\s*locale\.LC_(CTYPE|MESSAGES|NUMERIC)")),
    ("python", "CASE", "LINGUISTIC_REPAIR", R(r"\.lower\(\)"), R(r"\.casefold\(\)")),
    ("go", "CASE", "MACHINE_PINNING", R(r"ToLowerSpecial|ToUpperSpecial|cases\.(Lower|Upper)\(language\.(Turkish|Azerbaijani|Make)"), R(r"strings\.To(Lower|Upper)\(|cases\.(Lower|Upper)\(language\.(Und|English)")),
    ("rust", "CASE", "MACHINE_PINNING", R(r"\.to_(lowercase|uppercase)\(\)"), R(r"\.to_ascii_(lowercase|uppercase)\(\)|\.eq_ignore_ascii_case\(|make_ascii_(lowercase|uppercase)")),
    ("php", "CASE", "MACHINE_PINNING", R(r"(?<![\w>:])(strtolower|strtoupper|ucfirst|lcfirst|ucwords|stristr|strcasecmp|strncasecmp|stripos)\s*\("), R(r"(?i:ascii)|strtr\([^)]*['\"]ABCDEFGHIJKLMNOPQRSTUVWXYZ|mb_str(to)?(lower|upper)\([^)]*['\"](UTF-?8|ASCII)['\"]")),
    ("ruby", "CASE", "MACHINE_PINNING", R(r"\.(downcase|upcase|capitalize|swapcase)\b(?!\(:ascii)"), R(r"\.(downcase|upcase|capitalize|swapcase)\(:ascii\)")),
    ("shell_build", "ENV", "MACHINE_PINNING", R(r"(?=)"), R(r"\b(LC_ALL|LC_COLLATE|LC_CTYPE|LANG)=(C|POSIX|C\.UTF-8|en_US\.UTF-8)\b")),
    ("sql", "COLLATION", "MACHINE_PINNING", R(r"(?=)"), R(r"COLLATE\s+\"?(C|POSIX|ucs_basic|pg_c_utf8|binary|utf8mb4_bin|Latin1_General_BIN2?)\"?")),
]

MSG = {
    # Turkish letters are matched case-sensitively: under re.IGNORECASE Python treats U+0130/U+0131 as case variants of i/I.
    "turkic": re.compile(r"(?i:turk|tr[_-]tr\b|\btr locale|dotless|dotted ?i|azer|\baz[_-]az\b|lithuan)|[\u0130\u0131]"),
    "failure": re.compile(r"(?i)\b(fix(es|ed)?|bug|issue|broken|break(s|ing)?|fail(s|ed|ure|ing)?|crash(es)?|exception|error|wrong|incorrect|regression)\b"),
    "analyzer": re.compile(r"(?i)\bCA1(30[4-9]|31[01]|862)\b|error-?prone|spotbugs|findbugs|DM_CONVERT_CASE|forbidden-?apis|\bpmd\b|sonar|lint|checkstyle|StringCaseLocaleUsage|DefaultLocale|code analysis|analy[sz]er|static analysis|inspection|warning"),
    "issue_ref": re.compile(r"(#\d+\b|\b[A-Z][A-Z0-9]+-\d+\b|issues/\d+|bugs?\.\w+)"),
    "test_word": re.compile(r"(?i)\btests?\b"),
    # POST_HOC (added after the year distribution was inspected): coding-agent co-authorship trailers.
    "ai_agent": re.compile(r"(?i)co-authored-by:[^\n]*(copilot|claude|cursor|codex|devin|gemini|openhands|aider|anthropic|openai|jules)|generated with \[?claude|\U0001F916|copilot-swe-agent|coderabbit|\bcodex\b"),
    "bot": re.compile(r"(?i)openrewrite|rewrite recipe|automated|\bbot\b|dependabot|renovate|refaster|autofix"),
}
TEST_PATH = re.compile(r"(?i)(^|/)(test|tests|testing|spec|specs|__tests__|androidTest|testFixtures)/|Tests?\.(java|kt|cs|scala|groovy)$|_test\.(go|py|c|cc|cpp|rb)$|(^|/)test_\w+\.py$|\.(test|spec)\.(js|ts|jsx|tsx|mjs)$|Spec\.(groovy|scala|kt)$")


def ecosystem(fn):
    low = fn.lower(); base = low.rsplit("/", 1)[-1]
    if base in BUILD_NAMES or base.startswith("dockerfile"):
        return "shell_build"
    for k, exts in EXT.items():
        if low.endswith(exts):
            return k
    return None


def hunks(patch):
    cur = []
    for line in patch.split("\n"):
        if line.startswith("@@"):
            if cur: yield cur
            cur = []
        else:
            cur.append(line)
    if cur: yield cur


def norm(s):
    return re.sub(r"\s+", " ", s).strip()


def classify_file(fn, patch):
    eco = ecosystem(fn)
    if not eco or not patch:
        return eco, []
    edits = []
    rules = [r for r in RULES if r[0] == eco]
    for h in hunks(patch):
        rem = [l[1:] for l in h if l.startswith("-") and not l.startswith("---")]
        add = [l[1:] for l in h if l.startswith("+") and not l.startswith("+++")]
        if eco in ("shell_build", "sql"):
            for (_, op, d, S, T) in rules:
                for a in add:
                    if T.search(a) and not any(T.search(r) for r in rem) and not a.lstrip().startswith(("#", "--", "//")):
                        edits.append((op, d, "", norm(a)))
            continue
        used = set()
        for (_, op, d, S, T) in rules:
            for r in rem:
                if not S.search(r) or r.lstrip().startswith(("//", "#", "*", "/*")):
                    continue
                best, bi = 0.0, None
                for i, a in enumerate(add):
                    if i in used or not T.search(a):
                        continue
                    # the target must not still contain the same sensitive construct (except where S==T family overlap is intended)
                    if S.search(a) and not T.search(a):
                        continue
                    ratio = difflib.SequenceMatcher(None, norm(r), norm(a)).ratio()
                    if ratio > best:
                        best, bi = ratio, i
                if bi is not None and best >= 0.5:
                    used.add(bi)
                    edits.append((op, d, norm(r), norm(add[bi])))
    return eco, edits


def fingerprint(edits):
    return hashlib.sha256(json.dumps(sorted(e[2] + "→" + e[3] for e in edits)).encode()).hexdigest()[:20]


def main():
    cdir = ROOT / "data/raw/commits"; rdir = ROOT / "data/raw/repos"
    out = ROOT / "data/processed"; out.mkdir(parents=True, exist_ok=True)
    rows, edit_rows = [], []
    sys.path.insert(0, str(ROOT / "src"))
    import fetch_details
    allowed = set(fetch_details.candidates())  # deduplicated, non-merge, literal-filtered candidate SHAs
    for f in sorted(cdir.glob("*.json.gz")):
        if f.name[:-8] not in allowed:
            continue
        c = json.load(gzip.open(f, "rt"))
        if c.get("status") != 200 or "files" not in c:
            rows.append({"sha": c["sha"], "repo": c["repo"], "fetch_status": c.get("status"), "included": 0}); continue
        all_edits, ecos, test_change = [], set(), False
        for fl in c["files"]:
            fn = fl["filename"]
            if TEST_PATH.search(fn):
                test_change = True
            eco, edits = classify_file(fn, fl.get("patch", ""))
            for e in edits:
                ecos.add(eco); all_edits.append((eco, fn) + e)
        scope = [e for e in all_edits if e[2] != "FORMAT"]
        repo = {}
        rp = rdir / (c["repo"].replace("/", "__") + ".json")
        if rp.exists():
            repo = json.loads(rp.read_text())
        msg = c["message"]
        row = {"sha": c["sha"], "repo": c["repo"], "fetch_status": 200, "committer_date": c["committer_date"],
               "queries": ";".join(c["queries"]), "n_files": c.get("n_files_api"), "files_truncated": int((c.get("n_files_api") or 0) >= 300),
               "n_edits_all": len(all_edits), "n_edits_scope": len(scope), "included": int(bool(scope)),
               "format_only": int(bool(all_edits) and not scope),
               "ecosystems": ";".join(sorted({e[0] for e in scope})),
               "ops": ";".join(sorted({e[2] for e in scope})), "directions": ";".join(sorted({e[3] for e in scope})),
               "test_change": int(test_change),
               **{f"msg_{k}": int(bool(v.search(msg))) for k, v in MSG.items()},
               "fingerprint": fingerprint([e[2:] for e in scope]) if scope else "",
               "stars": repo.get("stargazers_count"), "repo_fork": repo.get("fork"), "repo_parent": repo.get("parent"),
               "repo_language": repo.get("language"), "repo_archived": repo.get("archived"),
               "subject": msg.split("\n", 1)[0][:200]}
        rows.append(row)
        for e in scope:
            edit_rows.append({"sha": c["sha"], "repo": c["repo"], "ecosystem": e[0], "file": e[1], "op": e[2], "direction": e[3],
                              "removed": e[4][:300], "added": e[5][:300], "test_file": int(bool(TEST_PATH.search(e[1])))})
    keys = sorted({k for r in rows for k in r})
    with open(out / "commits_classified.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys); w.writeheader(); w.writerows(rows)
    with open(out / "repair_edits.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(edit_rows[0]) if edit_rows else ["sha"]); w.writeheader(); w.writerows(edit_rows)
    print("commits", len(rows), "included", sum(r.get("included", 0) for r in rows), "edits", len(edit_rows))


if __name__ == "__main__":
    main()
