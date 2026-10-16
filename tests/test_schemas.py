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
