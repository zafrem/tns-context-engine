import pytest

from helpers import ROOT, load_yaml, meta, rel

NEGATIVE_TYPES = {"negation", "quotation", "news_report"}
POSITIVE_TYPES = {"target_person", "imperative"}


@pytest.mark.parametrize("path", sorted(ROOT.glob("context/*.yml")), ids=rel)
def test_adjust_sign_matches_rule_type_and_ids_unique(path):
    rules = load_yaml(path)["rules"]
    assert len({r["id"] for r in rules}) == len(rules)
    for r in rules:
        if r["type"] in NEGATIVE_TYPES:
            assert r["adjust"] <= 0, f"{r['id']}: {r['type']} must lower the score"
        if r["type"] in POSITIVE_TYPES:
            assert r["adjust"] >= 0, f"{r['id']}: {r['type']} must raise the score"


@pytest.mark.parametrize("lang", meta()["languages"])
def test_every_language_has_context_file(lang):
    assert (ROOT / "context" / f"{lang}.yml").exists()
