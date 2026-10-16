import re
import warnings
from collections import defaultdict

import pytest

from helpers import lexicon_entries, lexicon_files, load_yaml, meta, registry, rel

from regexcheck import regex_problems

try:  # authoritative RE2 check when installed
    import re2
except ImportError:  # pragma: no cover
    re2 = None


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
    problems = regex_problems(entry["term"], entry.get("flags", []), re2)
    assert not problems, f"{entry['id']}: {problems}"
    assert entry.get("hit_keywords") or entry.get("always_run") is True, (
        f"{entry['id']}: regex needs hit_keywords or always_run: true"
    )


def test_regex_check_rejects_non_re2_constructs_even_without_re2():
    for bad in [r"telegram\Z", r"(t)?(?(1)elegram|x)", r"(a)\1", r"(?=a)b", r"(?<!a)b", r"a++", r"x\G", r"(?>a)"]:
        assert regex_problems(bad, [], None), bad


def test_regex_check_accepts_re2_unicode_classes_and_escaped_plus():
    for ok in [r"\p{Han}{2,}", r"\p{Hangul}+", r"\pL+", r"\++", r"a\\1"]:
        assert regex_problems(ok, [], None) == [], ok


def test_regex_check_reports_invalid_patterns():
    assert regex_problems("(unclosed", [], None)


def test_re2_is_available_for_authoritative_regex_checking():
    pytest.importorskip("re2", reason="install .[re2] for the authoritative RE2 compile check")
    assert regex_problems(r"\p{Hangul}+", ["IGNORECASE"], re2) == []


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
