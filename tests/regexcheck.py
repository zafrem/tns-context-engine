"""RE2-subset check for lexicon regex entries. Test-only; not an engine."""
import re

UNSUPPORTED = (r"\Z", r"\G", "(?(", "(?=", "(?!", "(?<=", "(?<!", "(?P=", "(?>")
_UNICODE_CLASS = re.compile(r"\\[pP](?:\{[^}]*\}|[A-Za-z])")


def regex_problems(pattern, flags=(), re2_module=None):
    """Return a list of problems; empty means the pattern is acceptable.

    With `re2_module` (google-re2) the RE2 compile is authoritative. Without it,
    unsupported constructs are rejected lexically and the pattern is compiled with
    Python `re` after replacing RE2-only \\p{..} classes.
    """
    problems = []
    unescaped_backslashes = pattern.replace("\\\\", "")
    for bad in UNSUPPORTED:
        if bad in unescaped_backslashes:
            problems.append(f"{bad} is not in the RE2 subset")
    no_escapes = re.sub(r"\\.", "", _UNICODE_CLASS.sub("", unescaped_backslashes))
    if re.search(r"\\[1-9]", unescaped_backslashes):
        problems.append("backreference is not in the RE2 subset")
    if re.search(r"[*+?}]\+", no_escapes):
        problems.append("possessive quantifier is not in the RE2 subset")
    if problems:
        return problems
    ignorecase = "IGNORECASE" in flags
    try:
        if re2_module is not None:
            re2_module.compile(("(?i)" if ignorecase else "") + pattern)
        else:
            re.compile(_UNICODE_CLASS.sub("x", pattern), re.IGNORECASE if ignorecase else 0)
    except Exception as exc:  # re.error / re2 errors differ by backend
        problems.append(f"does not compile: {exc}")
    return problems
