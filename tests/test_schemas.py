import pytest
from jsonschema import Draft202012Validator

from helpers import ROOT, load_json, load_yaml, rel
from schema_map import GLOBS


def _format(errors):
    return "; ".join(
        f"{'/'.join(str(p) for p in e.absolute_path) or '<root>'}: {e.message}" for e in errors
    )


@pytest.mark.parametrize("path", sorted((ROOT / "schemas").glob("*.schema.json")), ids=rel)
def test_schema_is_valid_draft_2020_12(path):
    Draft202012Validator.check_schema(load_json(path))


@pytest.mark.parametrize("pattern,schema_name", GLOBS, ids=[g for g, _ in GLOBS])
def test_files_match_schema(pattern, schema_name):
    files = sorted(ROOT.glob(pattern))
    assert files, f"no files match {pattern}"
    validator = Draft202012Validator(load_json(ROOT / "schemas" / f"{schema_name}.schema.json"))
    for path in files:
        errors = sorted(validator.iter_errors(load_yaml(path)), key=lambda e: list(e.absolute_path))
        assert not errors, f"{rel(path)}: {_format(errors)}"


ALLOWED_EXTENSIONS = {".yml", ".json", ".jsonl", ".md"}
# Data files that are validated by dedicated tests instead of a GLOBS entry.
SCHEMA_EXEMPT = {"llm/output_schema.json", "eval/gold/gold.jsonl"}


def _data_files():
    from helpers import DATA_DIRS

    files = []
    for d in DATA_DIRS:
        files += [p for p in (ROOT / d).rglob("*") if p.is_file() and "__pycache__" not in p.parts]
    return sorted(files)


def test_every_data_file_has_an_allowed_extension():
    bad = [rel(p) for p in _data_files() if p.suffix not in ALLOWED_EXTENSIONS]
    assert not bad, f"unsupported extensions (use .yml, not .yaml): {bad}"


def test_every_yaml_file_is_covered_by_a_schema_glob():
    covered = set()
    for pattern, _ in GLOBS:
        covered.update(ROOT.glob(pattern))
    uncovered = [rel(p) for p in _data_files() if p.suffix == ".yml" and p not in covered]
    assert not uncovered, f"YAML files with no schema in tests/schema_map.py: {uncovered}"


def test_every_json_file_is_a_schema_or_exempt():
    unknown = [
        rel(p) for p in _data_files()
        if p.suffix == ".json" and p.parent.name != "schemas" and rel(p) not in SCHEMA_EXEMPT
    ]
    assert not unknown, f"JSON files with no validating test: {unknown}"
