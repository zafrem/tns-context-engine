"""Reference oracle for normalize/*.yml fixtures. Test-only; not an engine."""
import re
import unicodedata
from functools import lru_cache

from helpers import ROOT, load_yaml

_CHOSEONG = "ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ"
_JUNGSEONG = "ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ"
_JONGSEONG = (
    "", "ㄱ", "ㄲ", "ㄳ", "ㄴ", "ㄵ", "ㄶ", "ㄷ", "ㄹ", "ㄺ", "ㄻ", "ㄼ", "ㄽ", "ㄾ", "ㄿ", "ㅀ",
    "ㅁ", "ㅂ", "ㅄ", "ㅅ", "ㅆ", "ㅇ", "ㅈ", "ㅊ", "ㅋ", "ㅌ", "ㅍ", "ㅎ",
)


def _compose_jamo(text: str) -> str:
    out: list[str] = []
    n = len(text)
    i = 0
    while i < n:
        c = text[i]
        l_idx = _CHOSEONG.find(c)
        if l_idx != -1 and i + 1 < n:
            v_idx = _JUNGSEONG.find(text[i + 1])
            if v_idx != -1:
                t_idx = 0
                step = 2
                if i + 2 < n and text[i + 2] in _JONGSEONG[1:]:
                    if i + 3 >= n or _JUNGSEONG.find(text[i + 3]) == -1:
                        t_idx = _JONGSEONG.index(text[i + 2])
                        step = 3
                out.append(chr(0xAC00 + (l_idx * 21 + v_idx) * 28 + t_idx))
                i += step
                continue
        out.append(c)
        i += 1
    return "".join(out)


def _apply(rule, text):
    kind = rule["type"]
    if kind == "strip":
        return text.translate({ord(c): None for c in rule["chars"]})
    if kind == "map":
        return text.translate({ord(k): v for k, v in rule["mapping"].items()})
    if kind == "nfkc":
        return unicodedata.normalize("NFKC", text)
    if kind == "compose_jamo":
        return _compose_jamo(text)
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
