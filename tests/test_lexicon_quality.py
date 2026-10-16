from helpers import ROOT, lexicon_entries, load_yaml, meta
from normalizer_ref import normalize, rules_for


def test_terms_are_trimmed_and_already_normalized():
    for path, doc, e in lexicon_entries():
        if e["type"] == "regex":
            continue
        term = e["term"]
        assert term == term.strip(), f"{e['id']}: leading/trailing whitespace"
        assert normalize(term, rules_for(doc["lang"])) == term, (
            f"{e['id']}: term {term!r} changes under {doc['lang']} normalization and could never match"
        )


def test_no_duplicate_terms_after_normalization():
    seen = {}
    for _, doc, e in lexicon_entries():
        if e["type"] == "regex":
            continue
        key = (doc["lang"], normalize(e["term"], rules_for(doc["lang"])).casefold())
        assert key not in seen, f"{e['id']} duplicates {seen[key]}"
        seen[key] = e["id"]


def test_no_entry_is_a_stopword():
    stop = {lang: set(load_yaml(ROOT / "stopwords" / f"{lang}.yml")["words"]) for lang in meta()["languages"]}
    for _, doc, e in lexicon_entries():
        assert e["term"].casefold() not in stop.get(doc["lang"], set()), f"{e['id']} is a stopword"
