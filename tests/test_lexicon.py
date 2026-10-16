import re
import warnings
from collections import defaultdict

import pytest

from helpers import lexicon_entries, lexicon_files, load_yaml, meta, registry, rel

try:  # optional stricter check
    import re2
except ImportError:  # pragma: no cover
    re2 = None

FLAG_MAP = {"IGNORECASE": re.IGNORECASE}
FORBIDDEN_CONSTRUCTS = ("(?=", "(?!", "(?<=", "(?<!", "(?P=", "(?>")


@pytest.mark.parametrize("path", lexicon_files(), ids=rel)
def test_namespace_lang_and_id_prefix(path):
    doc = load_yaml(path)
    directory = path.parent.name
    if directory == "patterns":
        assert doc["lang"] == "und"
        assert doc["namespace"] == f"patterns.{path.stem}"
    else:
        assert doc["lang"] == path.stem
        assert doc["namespace"] == f"{directory}.{path.stem}"
    prefix = doc["namespace"].replace(".", "_") + "_"
    for e in doc["entries"]:
        assert e["id"].startswith(prefix), f"{e['id']} must start with {prefix}"


def test_entry_ids_are_unique_across_repo():
    seen = {}
    for path, _, e in lexicon_entries():
        assert e["id"] not in seen, f"{e['id']} in {rel(path)} duplicates {seen[e['id']]}"
        seen[e["id"]] = rel(path)


def test_concepts_exist_and_match_directory_series():
    codes = set(registry().values())
    cats = meta()["categories"]
    for path, _, e in lexicon_entries():
        assert e["concept"] in codes, f"{e['id']}: unknown concept {e['concept']}"
        directory = path.parent.name
        if directory != "patterns":
            assert e["concept"] // 1000 == cats[directory], f"{e['id']}: concept outside {directory} series"


def _regex_entries():
    return [(p, e) for p, _, e in lexicon_entries() if e["type"] == "regex"]


@pytest.mark.parametrize("path,entry", _regex_entries(), ids=lambda v: v["id"] if isinstance(v, dict) else rel(v))
def test_regex_is_re2_subset_compiles_and_is_gated(path, entry):
    pattern = entry["term"]
    stripped = pattern.replace("\\\\", "")  # drop escaped backslashes before looking for constructs
    for bad in FORBIDDEN_CONSTRUCTS:
        assert bad not in stripped, f"{entry['id']}: {bad} is not in the RE2 subset"
    assert not re.search(r"\\[1-9]", stripped), f"{entry['id']}: backreference not allowed"
    flags = 0
    for f in entry.get("flags", []):
        flags |= FLAG_MAP.get(f, 0)
    re.compile(pattern, flags)
    if re2 is not None:
        re2.compile(pattern)
    assert entry.get("hit_keywords") or entry.get("always_run") is True, (
        f"{entry['id']}: regex needs hit_keywords or always_run: true"
    )


def test_language_coverage_report():
    langs = set(meta()["languages"])
    seen = defaultdict(set)
    for _, doc, e in lexicon_entries():
        if doc["lang"] in langs:
            seen[e["concept"]].add(doc["lang"])
    gaps = {c: sorted(langs - got) for c, got in seen.items() if langs - got}
    uncovered = sorted(c for c in registry().values() if c not in seen and c // 1000 != 9)
    if gaps or uncovered:  # report only; never fails
        warnings.warn(f"coverage gaps: {gaps}; concepts with no entries: {uncovered}")
