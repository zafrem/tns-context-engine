import pytest
from jsonschema import Draft202012Validator

from helpers import ROOT, load_json, meta


def validator(name):
    return Draft202012Validator(load_json(ROOT / "schemas" / f"{name}.schema.json"))


VALID = {
    "nlp_request": {"text": "원금보장 수익", "lang": "ko", "spans": [{"span": [0, 4], "concept": 3001}]},
    "nlp_result": {"score": 70, "signals": {"negation": False, "quotation": False, "target_person": False, "intent": "solicitation", "sentiment": -0.2}},
    "llm_request": {"text": "guaranteed returns", "lang": "en", "spans": [{"span": [0, 18], "concept": 3001}], "prompt_template_id": "fraud.en"},
    "llm_verdict": {"scores": {"fraud": 82}, "label": "probable", "model_id": "llm.judge.fraud.en", "prompt_version": 1},
    "detection": {"span": [12, 18], "concept": 3001, "category": "fraud", "score": 82, "label": "probable", "action": "review", "stage_reached": 2, "matched_entry_ids": ["fraud_ko_0001"], "signals": {"negation": False}},
}
INVALID = {
    "nlp_request": {"text": "x", "lang": "zh", "spans": []},          # uppercase/short tag not allowed
    "nlp_result": {"score": 101, "signals": {}},
    "llm_request": {"text": "x", "lang": "en", "spans": []},            # missing prompt_template_id
    "llm_verdict": {"scores": {"fraud": 120}, "label": "probable", "model_id": "m", "prompt_version": 1},
    "detection": {"span": [3, 1], "concept": 3001, "category": "fraud", "score": 82, "label": "probable", "action": "shout", "stage_reached": 2, "matched_entry_ids": []},
}


@pytest.mark.parametrize("name", sorted(VALID))
def test_valid_example_passes(name):
    errors = list(validator(name).iter_errors(VALID[name]))
    assert not errors, [e.message for e in errors]


@pytest.mark.parametrize("name", sorted(INVALID))
def test_invalid_example_fails(name):
    assert list(validator(name).iter_errors(INVALID[name]))


@pytest.mark.parametrize("name", ["nlp_request", "llm_request"])
def test_language_enum_matches_meta(name):
    schema = load_json(ROOT / "schemas" / f"{name}.schema.json")
    assert schema["properties"]["lang"]["enum"] == meta()["languages"]


def test_llm_output_schema_is_valid_and_covers_all_categories():
    schema = load_json(ROOT / "llm" / "output_schema.json")
    Draft202012Validator.check_schema(schema)
    cats = {c for c in meta()["categories"] if c != "cross_cutting"}
    assert set(schema["properties"]["scores"]["required"]) == cats
