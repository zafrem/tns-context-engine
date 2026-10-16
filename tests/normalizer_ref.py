"""Reference oracle for normalize/*.yml fixtures. Test-only; not an engine."""
import re
import unicodedata
from functools import lru_cache

from helpers import ROOT, load_yaml


def _apply(rule, text):
    kind = rule["type"]
    if kind == "strip":
        return text.translate({ord(c): None for c in rule["chars"]})
    if kind == "map":
        return text.translate({ord(k): v for k, v in rule["mapping"].items()})
    if kind == "nfkc":
        return unicodedata.normalize("NFKC", text)
    if kind == "strip_between":
        chars = "".join(re.escape(c) for c in rule["chars"])
        between = rule["between"]
        return re.sub(f"(?<=[{between}])[{chars}]+(?=[{between}])", "", text)
    if kind == "collapse_repeats":
        n = rule["max_run"]
        return re.sub(rf"(.)\1{{{n},}}", lambda m: m.group(1) * n, text, flags=re.DOTALL)
    raise ValueError(f"unknown rule type {kind!r}")


def normalize(text, rules):
    for rule in rules:
        text = _apply(rule, text)
    return text


@lru_cache(maxsize=None)
def _rules_cached(lang):
    return tuple(load_yaml(ROOT / "normalize" / f"{lang}.yml")["rules"])


def rules_for(lang):
    if lang == "und":
        return []
    return list(_rules_cached(lang))
