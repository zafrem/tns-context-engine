import json

import pytest
from jsonschema import Draft202012Validator

from helpers import ROOT, load_json, meta, read_text, registry

GOLD = ROOT / "eval" / "gold" / "gold.jsonl"


def samples():
    return [json.loads(line) for line in read_text(GOLD).splitlines() if line.strip()]


def check_span_text(sample):
    """Each label's span must cut exactly span_text out of text (code point offsets)."""
    for label in sample["labels"]:
        start, end = label["span"]
        got = sample["text"][start:end]
        assert got == label["span_text"], f"span {label['span']} cuts {got!r}, expected {label['span_text']!r}"


def test_span_text_check_rejects_utf8_byte_offsets():
    sample = {"text": "원금보장 지금", "labels": [{"concept": 3001, "span": [0, 12], "span_text": "원금보장"}]}
    with pytest.raises(AssertionError):
        check_span_text(sample)
    sample["labels"][0]["span"] = [0, 4]
    check_span_text(sample)


def test_span_text_check_rejects_utf16_offsets_after_emoji():
    sample = {"text": "😀 원금보장", "labels": [{"concept": 3001, "span": [3, 7], "span_text": "원금보장"}]}
    with pytest.raises(AssertionError):  # UTF-16 offsets are +1 after an emoji; code points are [2, 6]
        check_span_text(sample)


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
    check_span_text(sample)


def test_metrics_doc_exists():
    assert (ROOT / "eval" / "METRICS.md").read_text(encoding="utf-8").strip()
