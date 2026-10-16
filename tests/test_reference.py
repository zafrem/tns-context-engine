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


def append_only_violations(released, current):
    """Problems if `current` is not an append-only extension of the `released` snapshot."""
    problems = []
    for name, code in released.items():
        if name not in current:
            problems.append(f"released concept {name} was removed; set deprecated: true instead")
        elif current[name] != code:
            problems.append(f"released code for {name} changed ({code} -> {current[name]})")
    reused = {c for c in released.values()} & {c for n, c in current.items() if n not in released}
    problems += [f"released code {c} was reused by a new concept" for c in sorted(reused)]
    return problems


def test_append_only_check_detects_removal_renumbering_and_reuse():
    released = {"fraud_phishing": 3002, "fraud_romance_scam": 3003}
    assert append_only_violations(released, dict(released, fraud_new=3005)) == []
    assert any("removed" in p for p in append_only_violations(released, {"fraud_phishing": 3002}))
    assert any("changed" in p for p in append_only_violations(released, {"fraud_phishing": 3005, "fraud_romance_scam": 3003}))
    assert any("reused" in p for p in append_only_violations(released, {"fraud_phishing": 3002, "fraud_new": 3003}))


def test_codes_are_append_only_against_released_snapshot():
    released = load_yaml(ROOT / "reference" / "released.yml")["codes"]
    assert append_only_violations(released, registry()) == []
