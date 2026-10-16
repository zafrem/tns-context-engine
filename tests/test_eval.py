import json

import pytest
from jsonschema import Draft202012Validator

from helpers import ROOT, load_json, meta, read_text, registry

GOLD = ROOT / "eval" / "gold" / "gold.jsonl"


def samples():
    return [json.loads(line) for line in read_text(GOLD).splitlines() if line.strip()]


def test_gold_set_not_empty_and_covers_every_language():
    langs = {s["lang"] for s in samples()}
    assert langs == set(meta()["languages"])


@pytest.mark.parametrize("sample", samples(), ids=lambda s: f"{s['lang']}:{s['text'][:12]}")
def test_sample_valid_and_spans_are_code_point_ranges(sample):
    schema = Draft202012Validator(load_json(ROOT / "schemas" / "eval_sample.schema.json"))
    errors = list(schema.iter_errors(sample))
    assert not errors, [e.message for e in errors]
    assert sample["lang"] in meta()["languages"]
    codes = set(registry().values())
    for label in sample["labels"]:
        start, end = label["span"]
        assert 0 <= start < end <= len(sample["text"]), f"span {label['span']} outside text of length {len(sample['text'])}"
        assert label["concept"] in codes


def test_metrics_doc_exists():
    assert (ROOT / "eval" / "METRICS.md").read_text(encoding="utf-8").strip()
