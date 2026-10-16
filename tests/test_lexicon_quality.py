import re
import unicodedata

import pytest

from helpers import ROOT, lexicon_entries, load_yaml, meta
from normalizer_ref import normalize, rules_for

FULLWIDTH_ASCII = re.compile("[！-～]")


def _non_regex():
    return [(p, d, e) for p, d, e in lexicon_entries() if e["type"] != "regex"]


@pytest.mark.parametrize("path,doc,e", _non_regex(), ids=lambda v: v["id"] if isinstance(v, dict) and "id" in v else "")
def test_term_is_trimmed_and_already_normalized(path, doc, e):
    term = e["term"]
    assert term == term.strip(), f"{e['id']}: leading/trailing whitespace"
    assert not FULLWIDTH_ASCII.search(term), f"{e['id']}: full-width ASCII in term {term!r}"
    assert unicodedata.normalize("NFKC", term) == term or doc["lang"] == "ko", f"{e['id']}: term is not NFKC"
    assert normalize(term, rules_for(doc["lang"])) == term, (
        f"{e['id']}: term {term!r} changes under {doc['lang']} normalization and could never match"
    )


@pytest.mark.parametrize("lang", meta()["languages"])
def test_fullwidth_input_is_folded_for_every_language(lang):
    folded = normalize("ａＢｃ", rules_for(lang))  # ａＢｃ
    assert folded == "aBc", f"{lang}: full-width letters are not folded"


def test_no_duplicate_terms_after_normalization():
    seen = {}
    for _, doc, e in lexicon_entries():
        if e["type"] == "regex":
            continue
        key = (doc["lang"], normalize(e["term"], rules_for(doc["lang"])).casefold())
        assert key not in seen, f"{e['id']} duplicates {seen[key]}"
        seen[key] = e["id"]


def test_no_entry_is_a_stopword():
    stop = {
        lang: {w.casefold() for w in load_yaml(ROOT / "stopwords" / f"{lang}.yml")["words"]}
        for lang in meta()["languages"]
    }
    for _, doc, e in lexicon_entries():
        assert e["term"].casefold() not in stop.get(doc["lang"], set()), f"{e['id']} is a stopword"
