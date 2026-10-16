import pytest

from helpers import ROOT, load_yaml, meta, rel
from normalizer_ref import normalize


@pytest.mark.parametrize("path", sorted(ROOT.glob("normalize/*.yml")), ids=rel)
def test_fixtures_hold(path):
    doc = load_yaml(path)
    for fx in doc["fixtures"]:
        got = normalize(fx["input"], doc["rules"])
        assert got == fx["expected"], f"{rel(path)}: {fx['input']!r} -> {got!r}, expected {fx['expected']!r}"


@pytest.mark.parametrize("path", sorted(ROOT.glob("normalize/*.yml")), ids=rel)
def test_rule_ids_unique_and_map_keys_single_char(path):
    rules = load_yaml(path)["rules"]
    ids = [r["id"] for r in rules]
    assert len(ids) == len(set(ids))
    for r in rules:
        if r["type"] == "map":
            assert all(len(k) == 1 for k in r["mapping"]), f"{r['id']}: map keys must be single characters"


@pytest.mark.parametrize("lang", meta()["languages"])
def test_every_language_has_normalize_and_stopword_files(lang):
    assert (ROOT / "normalize" / f"{lang}.yml").exists()
    assert (ROOT / "stopwords" / f"{lang}.yml").exists()
