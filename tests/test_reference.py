import pytest

from helpers import ROOT, load_yaml, meta, registry


def concept_files():
    return [ROOT / "reference" / f"{c}.yml" for c in meta()["categories"]]


def test_registry_not_empty():
    assert registry()


def test_master_registry_matches_category_files():
    from_files = {}
    for path in concept_files():
        for c in load_yaml(path)["concepts"]:
            assert c["name"] not in from_files, f"duplicate concept name {c['name']}"
            from_files[c["name"]] = c["code"]
    assert registry() == from_files


def test_codes_are_unique():
    codes = list(registry().values())
    assert len(codes) == len(set(codes))


def test_codes_match_category_series_and_names():
    cats = meta()["categories"]
    for path in concept_files():
        doc = load_yaml(path)
        assert path.stem == doc["category"]
        assert doc["series"] == cats[doc["category"]]
        for c in doc["concepts"]:
            assert c["code"] // 1000 == doc["series"], f"{c['name']} outside series"
            assert c["name"].startswith(doc["category"] + "_"), c["name"]


def test_codes_are_append_only_against_released_snapshot():
    released = load_yaml(ROOT / "reference" / "released.yml")["codes"]
    current = registry()
    for name, code in released.items():
        assert name in current, f"released concept {name} was removed; set deprecated: true instead"
        assert current[name] == code, f"released code for {name} changed"
