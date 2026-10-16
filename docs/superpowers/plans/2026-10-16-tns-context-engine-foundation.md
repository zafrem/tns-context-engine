# tns-context-engine Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the data-and-contracts foundation (schemas, seed data, model registry, integration doc) plus the data-integrity test suite described in the spec.

**Architecture:** The repo holds declarative YAML/JSON data validated by JSON Schemas, plus a data-only `pytest` suite. Every data file type is added test-first: a schema, a schema-map entry, seed data, then cross-file integrity tests. There is no runtime engine and no model weights. The only "logic" is a ~40-line reference normalizer inside `tests/`, used to check normalizer fixtures and lexicon quality.

**Tech Stack:** Python >= 3.9, pytest, PyYAML, jsonschema (Draft 2020-12), optional google-re2.

**Spec:** `docs/superpowers/specs/2026-10-16-tns-context-engine-design.md`

## Global Constraints

- Language tags are BCP 47 subtags in **lowercase** everywhere (file names, `lang` fields, registry keys): `en`, `ko`, `ja`, `zh-hans`, `zh-hant`. The pseudo-language `und` is allowed only for `lexicon/patterns/*.yml`.
- Categories and code series: defamation 1xxx, hate 2xxx, fraud 3xxx, illegal 4xxx, cross_cutting 9xxx. Codes are append-only and never reused.
- `rank` is an integer 1-5. `ambiguity` is a number 0-1.
- Regex entries use the RE2 subset only (no backreferences, no lookaround) and must declare `hit_keywords` or `always_run: true`.
- Action vocabulary is the closed enum `block | review | flag | pass`.
- Models are pointers only. `revision` is pinned (never `main`/`master`). Tests never download models.
- Tests are data-only. All data files are UTF-8 without BOM, `.yml` or `.json`.
- Python `>=3.9`. Runtime dependencies: none. Test dependencies: `pytest>=7.0.0`, `pyyaml>=6.0`, `jsonschema>=4.17`; optional `google-re2>=1.0`.
- Do not add an engine, a data loader package, or model files to this repo.

## Review Focus

The spec is silent on these; each has a test in the owning task.

1. **Duplicate YAML keys** (PyYAML silently keeps the last one, so an entry can vanish unnoticed). Expected: loading fails loudly. Task 1.
2. **Empty YAML file or UTF-8 BOM** (`yaml.safe_load` returns `None`; a BOM breaks CJK-heavy files subtly). Expected: a clear failure naming the file. Task 1.
3. **Lexicon term not in normalized form** (e.g. leading/trailing whitespace, full-width letters, `4` that the normalizer would turn into `a`) so it can never match. Expected: test fails naming the entry. Task 4.
4. **Regex that is valid in Python but not RE2-safe, or has no prefilter gate.** Expected: test fails naming the entry. Task 3.
5. **Eval spans measured in the wrong unit or out of range** (code points, `start < end <= len(text)`; CJK and emoji make UTF-8 byte or UTF-16 offsets tempting). Expected: test fails naming the sample. Task 7.

---

## File Structure

```
pyproject.toml  pytest.ini  .gitignore  README.md  INTEGRATION.md
.github/workflows/tests.yml
reference/{meta,registry,released}.yml + {defamation,hate,fraud,illegal,cross_cutting}.yml
lexicon/{defamation,hate,fraud,illegal}/{en,ko,ja,zh-hans,zh-hant}.yml
lexicon/patterns/contact_redirect.yml
normalize/{en,ko,ja,zh-hans,zh-hant}.yml
context/{en,ko,ja,zh-hans,zh-hant}.yml
stopwords/{en,ko,ja,zh-hans,zh-hant}.yml
scoring/scoring.yml
models/registry.yml
llm/output_schema.json  llm/prompts/fraud.en.md
schemas/*.schema.json
eval/METRICS.md  eval/gold/gold.jsonl
tests/{helpers,schema_map,normalizer_ref}.py
tests/test_{layout,schemas,reference,lexicon,normalize,lexicon_quality,context,scoring,models,contracts,eval}.py
```

Deviation note: spec section 2 lists `scoring/weights/<category>.yml`, but spec section 6 puts per-category overrides inline in `scoring.yml`. This plan follows section 6; `weights/` is added only when a category needs more than `block_min`/`floor`.

Registry shape note: `reference/registry.yml` is `version` + `codes: {name: code}` (the flat map from the spec, nested under `codes` so it can carry a version).

---

### Task 1: Scaffold, loader helpers, layout tests

**Files:**
- Create: `pyproject.toml`, `pytest.ini`, `.gitignore`, `README.md` (overwrite), `reference/meta.yml`
- Create: `tests/helpers.py`
- Test: `tests/test_layout.py`

**Interfaces:**
- Produces (`tests/helpers.py`): `ROOT: Path`, `rel(path) -> str`, `read_text(path) -> str`, `load_yaml(path) -> Any`, `load_json(path) -> Any`, `meta() -> dict`, `registry() -> dict` (the `codes` map `name -> code`), `yaml_files() -> list[Path]`, `lexicon_files() -> list[Path]`, `lexicon_entries() -> list[tuple[Path, dict, dict]]`, `lang_named_files() -> list[Path]`, `CATEGORY_DIRS`.
- Produces (`reference/meta.yml`): keys `schema_version`, `data_version`, `languages`, `pseudo_languages`, `categories` (`name -> series int`), `actions`.

- [ ] **Step 1: Create the feature branch and environment**

```bash
cd /home/baruna/playground/data/tns-context-engine
git checkout -b feat/foundation
python3 -m venv .venv && . .venv/bin/activate
```

- [ ] **Step 2: Write `pyproject.toml`, `pytest.ini`, `.gitignore`**

`pyproject.toml`:
```toml
[build-system]
requires = ["setuptools>=64", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "tns-context-engine"
version = "0.1.0"
description = "Data and specification foundation for filtering defamation, hate, fraud and illegal content (en, ko, ja, zh-hans, zh-hant)."
readme = "README.md"
requires-python = ">=3.9"
dependencies = []

[project.optional-dependencies]
test = ["pytest>=7.0.0", "pyyaml>=6.0", "jsonschema>=4.17"]
re2 = ["google-re2>=1.0"]

# Data-only repository: nothing is importable.
[tool.setuptools]
packages = []
```

`pytest.ini`:
```ini
[pytest]
testpaths = tests
```

`.gitignore`:
```
.venv/
__pycache__/
.pytest_cache/
*.egg-info/
```

Then: `pip install -e ".[test]"`

- [ ] **Step 3: Write `reference/meta.yml`**

```yaml
schema_version: 1
data_version: "0.1.0"
languages: [en, ko, ja, zh-hans, zh-hant]
pseudo_languages: [und]
categories:
  defamation: 1
  hate: 2
  fraud: 3
  illegal: 4
  cross_cutting: 9
actions: [block, review, flag, pass]
```

- [ ] **Step 4: Write the failing tests `tests/test_layout.py`**

```python
import re

import pytest
import yaml

from helpers import ROOT, lang_named_files, load_yaml, meta, read_text, rel, yaml_files

LANG_RE = re.compile(r"^[a-z]{2,3}(-[a-z]{4})?$")


@pytest.mark.parametrize("path", yaml_files(), ids=rel)
def test_yaml_files_load_strictly(path):
    # load_yaml rejects BOM, empty documents and duplicate keys
    load_yaml(path)


def test_loader_rejects_duplicate_keys(tmp_path):
    p = tmp_path / "dup.yml"
    p.write_text("a: 1\na: 2\n", encoding="utf-8")
    with pytest.raises(yaml.YAMLError):
        load_yaml(p)


def test_loader_rejects_empty_document(tmp_path):
    p = tmp_path / "empty.yml"
    p.write_text("# only a comment\n", encoding="utf-8")
    with pytest.raises(ValueError, match="empty YAML document"):
        load_yaml(p)


def test_loader_rejects_bom(tmp_path):
    p = tmp_path / "bom.yml"
    p.write_bytes(b"\xef\xbb\xbfa: 1\n")
    with pytest.raises(ValueError, match="BOM"):
        read_text(p)


def test_meta_languages_are_lowercase_bcp47():
    m = meta()
    for lang in m["languages"] + m["pseudo_languages"]:
        assert LANG_RE.match(lang), f"language tag must be lowercase BCP 47: {lang!r}"
    assert m["languages"] == ["en", "ko", "ja", "zh-hans", "zh-hant"]


@pytest.mark.parametrize("path", lang_named_files(), ids=rel)
def test_lang_named_files_use_known_lowercase_tag(path):
    assert path.stem in meta()["languages"], f"{rel(path)}: unknown language tag {path.stem!r}"
    assert load_yaml(path)["lang"] == path.stem


def test_pyproject_version_matches_data_version():
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    version = re.search(r'^version\s*=\s*"([^"]+)"', text, re.M).group(1)
    assert version == meta()["data_version"]
```

- [ ] **Step 5: Run to verify failure**

Run: `pytest tests/test_layout.py -v`
Expected: collection ERROR `ModuleNotFoundError: No module named 'helpers'` (helpers not written yet).

- [ ] **Step 6: Write `tests/helpers.py`**

```python
"""Shared helpers for the data-integrity tests. Data-only: no engine logic."""
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CATEGORY_DIRS = ("defamation", "hate", "fraud", "illegal")
DATA_DIRS = (
    "lexicon", "normalize", "context", "stopwords", "scoring",
    "reference", "models", "llm", "schemas", "eval",
)


class _StrictLoader(yaml.SafeLoader):
    """SafeLoader that rejects duplicate mapping keys instead of keeping the last."""


def _no_duplicate_keys(loader, node, deep=False):
    seen = set()
    for key_node, _ in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in seen:
            raise yaml.constructor.ConstructorError(
                None, None, f"duplicate key: {key!r}", key_node.start_mark
            )
        seen.add(key)
    return yaml.SafeLoader.construct_mapping(loader, node, deep)


_StrictLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _no_duplicate_keys
)


def rel(path):
    p = Path(path)
    try:
        return str(p.relative_to(ROOT))
    except ValueError:
        return str(p)


def read_text(path):
    raw = Path(path).read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise ValueError(f"{rel(path)}: UTF-8 BOM not allowed")
    return raw.decode("utf-8")


def load_yaml(path):
    doc = yaml.load(read_text(path), Loader=_StrictLoader)
    if doc is None:
        raise ValueError(f"{rel(path)}: empty YAML document")
    return doc


def load_json(path):
    return json.loads(read_text(path))


def meta():
    return load_yaml(ROOT / "reference" / "meta.yml")


def registry():
    """name -> code map from reference/registry.yml."""
    return load_yaml(ROOT / "reference" / "registry.yml")["codes"]


def yaml_files():
    files = []
    for d in DATA_DIRS:
        files += sorted((ROOT / d).glob("**/*.yml"))
    return files


def lexicon_files():
    return sorted(ROOT.glob("lexicon/*/*.yml"))


def lang_named_files():
    """Files whose stem must be a language tag."""
    files = []
    for d in CATEGORY_DIRS:
        files += sorted((ROOT / "lexicon" / d).glob("*.yml"))
    for d in ("normalize", "context", "stopwords"):
        files += sorted((ROOT / d).glob("*.yml"))
    return files


def lexicon_entries():
    """[(path, doc, entry), ...] for every lexicon entry."""
    out = []
    for path in lexicon_files():
        doc = load_yaml(path)
        for entry in doc["entries"]:
            out.append((path, doc, entry))
    return out
```

Also create `tests/conftest.py` so tests can `from helpers import ...`:
```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `pytest tests/test_layout.py -v`
Expected: all PASS (`test_yaml_files_load_strictly[reference/meta.yml]` is the only parametrized file case; the `lang_named_files` test is collected with zero params and reported as skipped).

- [ ] **Step 8: Write a short `README.md`**

```markdown
# tns-context-engine

Data and specification foundation for filtering defamation, hate, fraud and
illegal content in English, Korean, Japanese and Chinese (Simplified and
Traditional). Modeled on `pii-pattern-engine`.

This repository contains data, JSON Schema contracts, a model registry (pointers
to Hugging Face only) and data-integrity tests. It contains **no runtime engine
and no model weights**. See `INTEGRATION.md` for the contract an engine must
implement and `docs/superpowers/specs/` for the design.

Languages (lowercase BCP 47): `en`, `ko`, `ja`, `zh-hans`, `zh-hant`.

## Tests

    python3 -m venv .venv && . .venv/bin/activate
    pip install -e ".[test]"      # add ,re2 for RE2 compile checks
    pytest -q
```

- [ ] **Step 9: Commit**

```bash
git add pyproject.toml pytest.ini .gitignore README.md reference/meta.yml tests docs
git commit -m "chore: scaffold data-only repo with strict YAML loader and layout tests"
```
(This also commits the spec and this plan under `docs/`.)

---

### Task 2: Schema harness and code registry

**Files:**
- Create: `schemas/meta.schema.json`, `schemas/registry.schema.json`, `schemas/concepts.schema.json`
- Create: `reference/registry.yml`, `reference/released.yml`, `reference/{defamation,hate,fraud,illegal,cross_cutting}.yml`
- Create: `tests/schema_map.py`
- Test: `tests/test_schemas.py`, `tests/test_reference.py`

**Interfaces:**
- Consumes: `helpers.{ROOT, rel, load_yaml, load_json, meta, registry}`.
- Produces: `schema_map.GLOBS: list[tuple[str, str]]` of `(glob relative to ROOT, schema name)` where schema name `x` means `schemas/x.schema.json`. Later tasks append to it.
- Produces: concept codes 1001-1003, 2001-2005, 3001-3004, 4001-4004, 9001-9002 with names `<category>_<name>` (used by later tasks).

- [ ] **Step 1: Write `tests/schema_map.py`**

```python
# (glob relative to repo root, schema name -> schemas/<name>.schema.json)
GLOBS = [
    ("reference/meta.yml", "meta"),
    ("reference/registry.yml", "registry"),
    ("reference/released.yml", "registry"),
    ("reference/defamation.yml", "concepts"),
    ("reference/hate.yml", "concepts"),
    ("reference/fraud.yml", "concepts"),
    ("reference/illegal.yml", "concepts"),
    ("reference/cross_cutting.yml", "concepts"),
]
```

- [ ] **Step 2: Write the failing tests**

`tests/test_schemas.py`:
```python
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
```

`tests/test_reference.py`:
```python
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
```

- [ ] **Step 3: Run to verify failure**

Run: `pytest tests/test_schemas.py tests/test_reference.py -v`
Expected: FAIL (`no files match reference/registry.yml`, missing schemas).

- [ ] **Step 4: Write the three schemas**

`schemas/meta.schema.json`:
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "reference/meta.yml",
  "type": "object",
  "additionalProperties": false,
  "required": ["schema_version", "data_version", "languages", "pseudo_languages", "categories", "actions"],
  "properties": {
    "schema_version": {"type": "integer", "minimum": 1},
    "data_version": {"type": "string", "pattern": "^[0-9]+\\.[0-9]+\\.[0-9]+$"},
    "languages": {
      "type": "array", "minItems": 1, "uniqueItems": true,
      "items": {"type": "string", "pattern": "^[a-z]{2,3}(-[a-z]{4})?$"}
    },
    "pseudo_languages": {
      "type": "array", "uniqueItems": true,
      "items": {"type": "string", "pattern": "^[a-z]{2,3}$"}
    },
    "categories": {
      "type": "object", "minProperties": 1,
      "propertyNames": {"pattern": "^[a-z][a-z_]*$"},
      "additionalProperties": {"type": "integer", "minimum": 1, "maximum": 9}
    },
    "actions": {
      "type": "array", "uniqueItems": true,
      "items": {"enum": ["block", "review", "flag", "pass"]}
    }
  }
}
```

`schemas/registry.schema.json` (used for both `registry.yml` and `released.yml`):
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "reference/registry.yml and reference/released.yml",
  "type": "object",
  "additionalProperties": false,
  "required": ["version", "codes"],
  "properties": {
    "version": {"type": "integer", "minimum": 0},
    "codes": {
      "type": "object",
      "propertyNames": {"pattern": "^[a-z][a-z0-9_]*$"},
      "additionalProperties": {"type": "integer", "minimum": 1000, "maximum": 9999}
    }
  }
}
```

`schemas/concepts.schema.json`:
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "reference/<category>.yml",
  "type": "object",
  "additionalProperties": false,
  "required": ["category", "series", "concepts"],
  "properties": {
    "category": {"type": "string", "pattern": "^[a-z][a-z_]*$"},
    "series": {"type": "integer", "minimum": 1, "maximum": 9},
    "concepts": {
      "type": "array", "minItems": 1,
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["code", "name", "description", "rank_default"],
        "properties": {
          "code": {"type": "integer", "minimum": 1000, "maximum": 9999},
          "name": {"type": "string", "pattern": "^[a-z][a-z0-9_]*$"},
          "description": {"type": "string", "minLength": 1},
          "rank_default": {"type": "integer", "minimum": 1, "maximum": 5},
          "deprecated": {"type": "boolean"}
        }
      }
    }
  }
}
```

- [ ] **Step 5: Write the registry data**

`reference/released.yml`:
```yaml
# Snapshot of the registry at the last release. Update only when cutting a release.
version: 0
codes: {}
```

`reference/registry.yml`:
```yaml
version: 1
# name -> stable code. Append-only; never reuse a code. See category files for details.
codes:
  defamation_insult: 1001
  defamation_false_accusation: 1002
  defamation_doxxing_threat: 1003
  hate_slur_ethnic: 2001
  hate_slur_gender: 2002
  hate_slur_religion: 2003
  hate_slur_disability: 2004
  hate_exclusion_incitement: 2005
  fraud_investment_scam: 3001
  fraud_phishing: 3002
  fraud_romance_scam: 3003
  fraud_impersonation: 3004
  illegal_drugs: 4001
  illegal_weapons: 4002
  illegal_illegal_gambling: 4003
  illegal_csam_solicitation: 4004
  cross_cutting_obfuscation_marker: 9001
  cross_cutting_contact_redirect: 9002
```

`reference/defamation.yml`:
```yaml
category: defamation
series: 1
concepts:
  - {code: 1001, name: defamation_insult, description: "Insulting or demeaning a person.", rank_default: 2}
  - {code: 1002, name: defamation_false_accusation, description: "Accusing a person of a crime or misconduct (e.g. fraudster); highly context dependent.", rank_default: 2}
  - {code: 1003, name: defamation_doxxing_threat, description: "Threatening to expose or exposing private information.", rank_default: 4}
```

`reference/hate.yml`:
```yaml
category: hate
series: 2
concepts:
  - {code: 2001, name: hate_slur_ethnic, description: "Slurs targeting ethnicity, nationality or race.", rank_default: 5}
  - {code: 2002, name: hate_slur_gender, description: "Slurs targeting gender or sexual orientation.", rank_default: 5}
  - {code: 2003, name: hate_slur_religion, description: "Slurs targeting religion.", rank_default: 5}
  - {code: 2004, name: hate_slur_disability, description: "Slurs targeting disability.", rank_default: 5}
  - {code: 2005, name: hate_exclusion_incitement, description: "Telling a group to leave or be excluded (e.g. 'go back to your country').", rank_default: 4}
```

`reference/fraud.yml`:
```yaml
category: fraud
series: 3
concepts:
  - {code: 3001, name: fraud_investment_scam, description: "Guaranteed-return or principal-protected investment pitches.", rank_default: 4}
  - {code: 3002, name: fraud_phishing, description: "Credential or payment harvesting lures.", rank_default: 4}
  - {code: 3003, name: fraud_romance_scam, description: "Romance-based financial manipulation.", rank_default: 3}
  - {code: 3004, name: fraud_impersonation, description: "Impersonating an institution or person to obtain money or data.", rank_default: 3}
```

`reference/illegal.yml`:
```yaml
category: illegal
series: 4
concepts:
  - {code: 4001, name: illegal_drugs, description: "Offers to sell or buy illegal drugs.", rank_default: 4}
  - {code: 4002, name: illegal_weapons, description: "Offers to sell or buy illegal weapons.", rank_default: 4}
  - {code: 4003, name: illegal_illegal_gambling, description: "Promotion of illegal gambling.", rank_default: 3}
  - {code: 4004, name: illegal_csam_solicitation, description: "Solicitation of child sexual abuse material.", rank_default: 5}
```

`reference/cross_cutting.yml`:
```yaml
category: cross_cutting
series: 9
concepts:
  - {code: 9001, name: cross_cutting_obfuscation_marker, description: "Evasion markers that raise suspicion when combined with other signals.", rank_default: 1}
  - {code: 9002, name: cross_cutting_contact_redirect, description: "Moving a conversation to a private channel (messenger IDs, phone numbers).", rank_default: 2}
```

- [ ] **Step 6: Run to verify pass**

Run: `pytest -q`
Expected: all PASS.

- [ ] **Step 7: Commit**

```bash
git add schemas reference tests
git commit -m "feat: add schema harness and stable concept code registry"
```

---

### Task 3: Lexicon schema, seed entries, structure and regex tests

**Files:**
- Create: `schemas/lexicon.schema.json`
- Create: `lexicon/defamation/{en,ko,ja,zh-hans,zh-hant}.yml`, same for `hate`, `fraud`, `illegal`, and `lexicon/patterns/contact_redirect.yml`
- Modify: `tests/schema_map.py` (append one entry)
- Test: `tests/test_lexicon.py`

**Interfaces:**
- Consumes: `helpers.{ROOT, rel, load_yaml, meta, registry, lexicon_files, lexicon_entries}`; concept names/codes from Task 2.
- Produces: lexicon entries with fields `id, concept, term, type, rank, ambiguity, requires_context?, always_run?, flags?, hit_keywords?, notes?`. File/namespace rules: category dir `D` + file `L.yml` has `namespace: D.L`, `lang: L`, ids `D_L_NNNN`; patterns file `P.yml` has `namespace: patterns.P`, `lang: und`, ids `patterns_P_NNNN`.

- [ ] **Step 1: Append to `tests/schema_map.py`**

```python
GLOBS += [
    ("lexicon/*/*.yml", "lexicon"),
]
```

- [ ] **Step 2: Write the failing tests `tests/test_lexicon.py`**

```python
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
```

- [ ] **Step 3: Run to verify failure**

Run: `pytest tests/test_lexicon.py tests/test_schemas.py -v`
Expected: FAIL (`no files match lexicon/*/*.yml`, missing `lexicon.schema.json`).

- [ ] **Step 4: Write `schemas/lexicon.schema.json`**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "lexicon/<category>/<lang>.yml and lexicon/patterns/*.yml",
  "type": "object",
  "additionalProperties": false,
  "required": ["namespace", "lang", "entries"],
  "properties": {
    "namespace": {"type": "string", "pattern": "^[a-z_]+\\.[a-z0-9_-]+$"},
    "lang": {"type": "string", "pattern": "^([a-z]{2,3}(-[a-z]{4})?)$"},
    "entries": {"type": "array", "minItems": 1, "items": {"$ref": "#/$defs/entry"}}
  },
  "$defs": {
    "entry": {
      "type": "object",
      "additionalProperties": false,
      "required": ["id", "concept", "term", "type", "rank", "ambiguity"],
      "properties": {
        "id": {"type": "string", "pattern": "^[a-z][a-z_]*_[a-z0-9-]+_[0-9]{4}$"},
        "concept": {"type": "integer", "minimum": 1000, "maximum": 9999},
        "term": {"type": "string", "minLength": 1},
        "type": {"enum": ["literal", "phrase", "regex"]},
        "rank": {"type": "integer", "minimum": 1, "maximum": 5},
        "ambiguity": {"type": "number", "minimum": 0, "maximum": 1},
        "requires_context": {"type": "boolean"},
        "always_run": {"type": "boolean"},
        "flags": {"type": "array", "uniqueItems": true, "items": {"enum": ["IGNORECASE", "WORD_BOUNDARY"]}},
        "hit_keywords": {"type": "array", "items": {"type": "string", "minLength": 1}},
        "notes": {"type": "string"}
      }
    }
  }
}
```
(`und` matches the `lang` pattern `[a-z]{2,3}`.)

- [ ] **Step 5: Write seed lexicon files**

`lexicon/defamation/en.yml`:
```yaml
namespace: defamation.en
lang: en
entries:
  - {id: defamation_en_0001, concept: 1002, term: fraudster, type: literal, rank: 2, ambiguity: 0.6, requires_context: true, flags: [IGNORECASE, WORD_BOUNDARY]}
```
`lexicon/defamation/ko.yml`:
```yaml
namespace: defamation.ko
lang: ko
entries:
  - {id: defamation_ko_0001, concept: 1002, term: 사기꾼, type: literal, rank: 2, ambiguity: 0.6, requires_context: true}
```
`lexicon/defamation/ja.yml`:
```yaml
namespace: defamation.ja
lang: ja
entries:
  - {id: defamation_ja_0001, concept: 1002, term: 詐欺師, type: literal, rank: 2, ambiguity: 0.6, requires_context: true}
```
`lexicon/defamation/zh-hans.yml`:
```yaml
namespace: defamation.zh-hans
lang: zh-hans
entries:
  - {id: defamation_zh-hans_0001, concept: 1002, term: 骗子, type: literal, rank: 2, ambiguity: 0.6, requires_context: true}
```
`lexicon/defamation/zh-hant.yml`:
```yaml
namespace: defamation.zh-hant
lang: zh-hant
entries:
  - {id: defamation_zh-hant_0001, concept: 1002, term: 騙子, type: literal, rank: 2, ambiguity: 0.6, requires_context: true}
```

`lexicon/hate/en.yml`:
```yaml
namespace: hate.en
lang: en
entries:
  - {id: hate_en_0001, concept: 2005, term: go back to your country, type: phrase, rank: 4, ambiguity: 0.3, flags: [IGNORECASE]}
```
`lexicon/hate/ko.yml`:
```yaml
namespace: hate.ko
lang: ko
entries:
  - {id: hate_ko_0001, concept: 2005, term: 너희 나라로 돌아가, type: phrase, rank: 4, ambiguity: 0.3}
```
`lexicon/hate/ja.yml`:
```yaml
namespace: hate.ja
lang: ja
entries:
  - {id: hate_ja_0001, concept: 2005, term: 国へ帰れ, type: phrase, rank: 4, ambiguity: 0.3}
```
`lexicon/hate/zh-hans.yml`:
```yaml
namespace: hate.zh-hans
lang: zh-hans
entries:
  - {id: hate_zh-hans_0001, concept: 2005, term: 滚回你的国家, type: phrase, rank: 4, ambiguity: 0.3}
```
`lexicon/hate/zh-hant.yml`:
```yaml
namespace: hate.zh-hant
lang: zh-hant
entries:
  - {id: hate_zh-hant_0001, concept: 2005, term: 滾回你的國家, type: phrase, rank: 4, ambiguity: 0.3}
```

`lexicon/fraud/en.yml`:
```yaml
namespace: fraud.en
lang: en
entries:
  - {id: fraud_en_0001, concept: 3001, term: guaranteed returns, type: phrase, rank: 4, ambiguity: 0.3, flags: [IGNORECASE]}
```
`lexicon/fraud/ko.yml`:
```yaml
namespace: fraud.ko
lang: ko
entries:
  - {id: fraud_ko_0001, concept: 3001, term: 원금보장, type: literal, rank: 4, ambiguity: 0.2}
```
`lexicon/fraud/ja.yml`:
```yaml
namespace: fraud.ja
lang: ja
entries:
  - {id: fraud_ja_0001, concept: 3001, term: 元本保証, type: literal, rank: 4, ambiguity: 0.2}
```
`lexicon/fraud/zh-hans.yml`:
```yaml
namespace: fraud.zh-hans
lang: zh-hans
entries:
  - {id: fraud_zh-hans_0001, concept: 3001, term: 稳赚不赔, type: literal, rank: 4, ambiguity: 0.2}
```
`lexicon/fraud/zh-hant.yml`:
```yaml
namespace: fraud.zh-hant
lang: zh-hant
entries:
  - {id: fraud_zh-hant_0001, concept: 3001, term: 穩賺不賠, type: literal, rank: 4, ambiguity: 0.2}
```

`lexicon/illegal/en.yml`:
```yaml
namespace: illegal.en
lang: en
entries:
  - {id: illegal_en_0001, concept: 4001, term: buy cocaine, type: phrase, rank: 4, ambiguity: 0.2, flags: [IGNORECASE]}
```
`lexicon/illegal/ko.yml`:
```yaml
namespace: illegal.ko
lang: ko
entries:
  - {id: illegal_ko_0001, concept: 4001, term: 마약 판매, type: phrase, rank: 4, ambiguity: 0.2}
```
`lexicon/illegal/ja.yml`:
```yaml
namespace: illegal.ja
lang: ja
entries:
  - {id: illegal_ja_0001, concept: 4001, term: 覚せい剤を売ります, type: phrase, rank: 4, ambiguity: 0.1}
```
`lexicon/illegal/zh-hans.yml`:
```yaml
namespace: illegal.zh-hans
lang: zh-hans
entries:
  - {id: illegal_zh-hans_0001, concept: 4001, term: 出售毒品, type: phrase, rank: 4, ambiguity: 0.2}
```
`lexicon/illegal/zh-hant.yml`:
```yaml
namespace: illegal.zh-hant
lang: zh-hant
entries:
  - {id: illegal_zh-hant_0001, concept: 4001, term: 販售毒品, type: phrase, rank: 4, ambiguity: 0.2}
```

`lexicon/patterns/contact_redirect.yml`:
```yaml
namespace: patterns.contact_redirect
lang: und
entries:
  - id: patterns_contact_redirect_0001
    concept: 9002
    term: '\b(whatsapp|telegram|kakaotalk)\b[^\n]{0,20}[0-9]{6,}'
    type: regex
    rank: 2
    ambiguity: 0.5
    flags: [IGNORECASE]
    hit_keywords: [whatsapp, telegram, kakaotalk]
```

- [ ] **Step 6: Run to verify pass**

Run: `pytest -q`
Expected: all PASS. `test_language_coverage_report` emits a warning listing concepts without entries or languages (expected for the seed set). Note: the lexicon schema's `lang` pattern deliberately has no `und` special case; `und` matches `[a-z]{2,3}`.

- [ ] **Step 7: Commit**

```bash
git add schemas/lexicon.schema.json lexicon tests
git commit -m "feat: add lexicon schema, seed entries and structure/regex integrity tests"
```

---

### Task 4: Normalization rules, stopwords, reference normalizer, lexicon quality tests

**Files:**
- Create: `schemas/normalize.schema.json`, `schemas/stopwords.schema.json`
- Create: `normalize/{en,ko,ja,zh-hans,zh-hant}.yml`, `stopwords/{en,ko,ja,zh-hans,zh-hant}.yml`
- Create: `tests/normalizer_ref.py`
- Modify: `tests/schema_map.py`
- Test: `tests/test_normalize.py`, `tests/test_lexicon_quality.py`

**Interfaces:**
- Consumes: `helpers`, lexicon entries from Task 3.
- Produces (`tests/normalizer_ref.py`): `normalize(text: str, rules: list[dict]) -> str`; `rules_for(lang: str) -> list[dict]` (`[]` for `und`). Rule types: `strip{chars}`, `map{mapping}`, `strip_between{chars, between}`, `nfkc`, `collapse_repeats{max_run}`. Rules apply in file order. This is a test fixture oracle only, not an engine.

- [ ] **Step 1: Append to `tests/schema_map.py`**

```python
GLOBS += [
    ("normalize/*.yml", "normalize"),
    ("stopwords/*.yml", "stopwords"),
]
```

- [ ] **Step 2: Write the failing tests**

`tests/test_normalize.py`:
```python
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
```

`tests/test_lexicon_quality.py`:
```python
from helpers import ROOT, lexicon_entries, load_yaml, meta
from normalizer_ref import normalize, rules_for


def test_terms_are_trimmed_and_already_normalized():
    for path, doc, e in lexicon_entries():
        if e["type"] == "regex":
            continue
        term = e["term"]
        assert term == term.strip(), f"{e['id']}: leading/trailing whitespace"
        assert normalize(term, rules_for(doc["lang"])) == term, (
            f"{e['id']}: term {term!r} changes under {doc['lang']} normalization and could never match"
        )


def test_no_duplicate_terms_after_normalization():
    seen = {}
    for _, doc, e in lexicon_entries():
        if e["type"] == "regex":
            continue
        key = (doc["lang"], normalize(e["term"], rules_for(doc["lang"])).casefold())
        assert key not in seen, f"{e['id']} duplicates {seen[key]}"
        seen[key] = e["id"]


def test_no_entry_is_a_stopword():
    stop = {lang: set(load_yaml(ROOT / "stopwords" / f"{lang}.yml")["words"]) for lang in meta()["languages"]}
    for _, doc, e in lexicon_entries():
        assert e["term"].casefold() not in stop.get(doc["lang"], set()), f"{e['id']} is a stopword"
```

- [ ] **Step 3: Run to verify failure**

Run: `pytest tests/test_normalize.py tests/test_lexicon_quality.py -v`
Expected: collection ERROR `ModuleNotFoundError: No module named 'normalizer_ref'`.

- [ ] **Step 4: Write `tests/normalizer_ref.py`**

```python
"""Reference oracle for normalize/*.yml fixtures. Test-only; not an engine."""
import re
import unicodedata
from functools import lru_cache

from helpers import ROOT, load_yaml


def _apply(rule, text):
    kind = rule["type"]
    if kind == "strip":
        return text.translate({ord(c): None for c in rule["chars"]})
    if kind == "map":
        return text.translate({ord(k): v for k, v in rule["mapping"].items()})
    if kind == "nfkc":
        return unicodedata.normalize("NFKC", text)
    if kind == "strip_between":
        chars = "".join(re.escape(c) for c in rule["chars"])
        between = rule["between"]
        return re.sub(f"(?<=[{between}])[{chars}]+(?=[{between}])", "", text)
    if kind == "collapse_repeats":
        n = rule["max_run"]
        return re.sub(rf"(.)\1{{{n},}}", lambda m: m.group(1) * n, text, flags=re.DOTALL)
    raise ValueError(f"unknown rule type {kind!r}")


def normalize(text, rules):
    for rule in rules:
        text = _apply(rule, text)
    return text


@lru_cache(maxsize=None)
def _rules_cached(lang):
    return tuple(load_yaml(ROOT / "normalize" / f"{lang}.yml")["rules"])


def rules_for(lang):
    if lang == "und":
        return []
    return list(_rules_cached(lang))
```

- [ ] **Step 5: Write the schemas**

`schemas/normalize.schema.json`:
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "normalize/<lang>.yml",
  "type": "object",
  "additionalProperties": false,
  "required": ["lang", "rules", "fixtures"],
  "properties": {
    "lang": {"type": "string", "pattern": "^[a-z]{2,3}(-[a-z]{4})?$"},
    "rules": {"type": "array", "minItems": 1, "items": {"$ref": "#/$defs/rule"}},
    "fixtures": {
      "type": "array", "minItems": 1,
      "items": {
        "type": "object", "additionalProperties": false,
        "required": ["input", "expected"],
        "properties": {"input": {"type": "string"}, "expected": {"type": "string"}}
      }
    }
  },
  "$defs": {
    "rule": {
      "type": "object",
      "required": ["id", "type"],
      "properties": {
        "id": {"type": "string", "pattern": "^[a-z][a-z0-9_]*$"},
        "type": {"enum": ["strip", "map", "strip_between", "nfkc", "collapse_repeats"]},
        "chars": {"type": "array", "minItems": 1, "items": {"type": "string", "minLength": 1, "maxLength": 1}},
        "mapping": {"type": "object", "minProperties": 1, "additionalProperties": {"type": "string"}},
        "between": {"type": "string", "minLength": 1},
        "max_run": {"type": "integer", "minimum": 1}
      },
      "additionalProperties": false,
      "allOf": [
        {"if": {"properties": {"type": {"const": "strip"}}}, "then": {"required": ["chars"]}},
        {"if": {"properties": {"type": {"const": "map"}}}, "then": {"required": ["mapping"]}},
        {"if": {"properties": {"type": {"const": "strip_between"}}}, "then": {"required": ["chars", "between"]}},
        {"if": {"properties": {"type": {"const": "collapse_repeats"}}}, "then": {"required": ["max_run"]}}
      ]
    }
  }
}
```

`schemas/stopwords.schema.json`:
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "stopwords/<lang>.yml",
  "type": "object",
  "additionalProperties": false,
  "required": ["lang", "words"],
  "properties": {
    "lang": {"type": "string", "pattern": "^[a-z]{2,3}(-[a-z]{4})?$"},
    "words": {"type": "array", "minItems": 1, "uniqueItems": true, "items": {"type": "string", "minLength": 1}}
  }
}
```

- [ ] **Step 6: Write the data files**

`normalize/en.yml`:
```yaml
lang: en
rules:
  - id: en_strip_invisible
    type: strip
    chars: ["​", "‌", "‍", "﻿"]
  - id: en_leetspeak
    type: map
    mapping: {"4": "a", "3": "e", "1": "i", "0": "o", "$": "s", "@": "a"}
  - id: en_collapse_repeats
    type: collapse_repeats
    max_run: 2
fixtures:
  - {input: "sc4m", expected: "scam"}
  - {input: "sc​am", expected: "scam"}
  - {input: "freeee", expected: "free"}
```

`normalize/ko.yml`:
```yaml
lang: ko
rules:
  - id: ko_strip_invisible
    type: strip
    chars: ["​", "‌", "‍", "﻿"]
  - id: ko_strip_inserted_symbols
    type: strip_between
    chars: [".", "-", "*", "·"]
    between: "가-힣"
fixtures:
  - {input: "원.금.보.장", expected: "원금보장"}
  - {input: "원*금-보·장", expected: "원금보장"}
```

`normalize/ja.yml`:
```yaml
lang: ja
rules:
  - id: ja_nfkc
    type: nfkc
  - id: ja_strip_inserted_symbols
    type: strip_between
    chars: [".", "-", "*", "・"]
    between: "぀-ヿ一-鿿"
fixtures:
  - {input: "ﾏﾈｰ", expected: "マネー"}
  - {input: "元.本.保.証", expected: "元本保証"}
```

`normalize/zh-hans.yml`:
```yaml
lang: zh-hans
rules:
  - id: zh_hans_nfkc
    type: nfkc
  - id: zh_hans_strip_inserted_symbols
    type: strip_between
    chars: [".", "-", "*", " "]
    between: "一-鿿"
fixtures:
  - {input: "稳*赚*不*赔", expected: "稳赚不赔"}
  - {input: "稳 赚 不 赔", expected: "稳赚不赔"}
```

`normalize/zh-hant.yml`:
```yaml
lang: zh-hant
rules:
  - id: zh_hant_nfkc
    type: nfkc
  - id: zh_hant_strip_inserted_symbols
    type: strip_between
    chars: [".", "-", "*", " "]
    between: "一-鿿"
fixtures:
  - {input: "穩*賺*不*賠", expected: "穩賺不賠"}
  - {input: "穩 賺 不 賠", expected: "穩賺不賠"}
```

`stopwords/en.yml`: `lang: en` / `words: [the, a, an, of, to]`
`stopwords/ko.yml`: `lang: ko` / `words: [은, 는, 이, 가, 을, 를]`
`stopwords/ja.yml`: `lang: ja` / `words: [の, は, が, を, に]`
`stopwords/zh-hans.yml`: `lang: zh-hans` / `words: [的, 了, 是, 在]`
`stopwords/zh-hant.yml`: `lang: zh-hant` / `words: [的, 了, 是, 在]`

(Each file is the two lines shown, e.g. `stopwords/en.yml` is `lang: en` newline `words: [the, a, an, of, to]`.)

- [ ] **Step 7: Run to verify pass**

Run: `pytest -q`
Expected: all PASS. If `test_terms_are_trimmed_and_already_normalized` fails for a seed term, fix the term (not the oracle).

- [ ] **Step 8: Commit**

```bash
git add schemas normalize stopwords tests
git commit -m "feat: add normalization rules, stopwords and lexicon quality tests"
```

---

### Task 5: Context rules and scoring configuration

**Files:**
- Create: `schemas/context.schema.json`, `schemas/scoring.schema.json`
- Create: `context/{en,ko,ja,zh-hans,zh-hant}.yml`, `scoring/scoring.yml`
- Modify: `tests/schema_map.py`
- Test: `tests/test_context.py`, `tests/test_scoring.py`

**Interfaces:**
- Consumes: `helpers`, `meta()["actions"]`, `meta()["categories"]`.
- Produces (`scoring/scoring.yml` keys): `version`, `rank_weight` (list of 5 ints; index = rank-1), `corroboration{step, cap}`, `fuse{method, weights{stage1,nlp,llm}}`, `floor{rank, min_score}`, `thresholds[{min,label,action}]` (descending), `category_overrides{<category>:{block_min?}}`, `router{definite_min, clean_below, nlp_confident_hi, nlp_confident_lo}`.
- Produces (`context/<lang>.yml`): `lang`, `rules[{id,type,terms[],adjust}]`, `type` in `negation|quotation|news_report|target_person|imperative`.

- [ ] **Step 1: Append to `tests/schema_map.py`**

```python
GLOBS += [
    ("context/*.yml", "context"),
    ("scoring/scoring.yml", "scoring"),
]
```

- [ ] **Step 2: Write the failing tests**

`tests/test_context.py`:
```python
import pytest

from helpers import ROOT, load_yaml, meta, rel

NEGATIVE_TYPES = {"negation", "quotation", "news_report"}
POSITIVE_TYPES = {"target_person", "imperative"}


@pytest.mark.parametrize("path", sorted(ROOT.glob("context/*.yml")), ids=rel)
def test_adjust_sign_matches_rule_type_and_ids_unique(path):
    rules = load_yaml(path)["rules"]
    assert len({r["id"] for r in rules}) == len(rules)
    for r in rules:
        if r["type"] in NEGATIVE_TYPES:
            assert r["adjust"] <= 0, f"{r['id']}: {r['type']} must lower the score"
        if r["type"] in POSITIVE_TYPES:
            assert r["adjust"] >= 0, f"{r['id']}: {r['type']} must raise the score"


@pytest.mark.parametrize("lang", meta()["languages"])
def test_every_language_has_context_file(lang):
    assert (ROOT / "context" / f"{lang}.yml").exists()
```

`tests/test_scoring.py`:
```python
from helpers import ROOT, load_yaml, meta

ACTION_ORDER = ["block", "review", "flag", "pass"]


def cfg():
    return load_yaml(ROOT / "scoring" / "scoring.yml")


def test_rank_weights_are_non_decreasing():
    w = cfg()["rank_weight"]
    assert w == sorted(w) and len(w) == 5


def test_thresholds_strictly_descending_end_at_zero_and_use_known_actions():
    t = cfg()["thresholds"]
    mins = [x["min"] for x in t]
    assert mins == sorted(mins, reverse=True) and len(set(mins)) == len(mins)
    assert mins[-1] == 0
    assert all(x["action"] in meta()["actions"] for x in t)
    idx = [ACTION_ORDER.index(x["action"]) for x in t]
    assert idx == sorted(idx), "actions must get milder as score decreases"


def test_category_overrides_are_known_and_keep_review_band():
    review_min = min(x["min"] for x in cfg()["thresholds"] if x["action"] == "review")
    for cat, o in cfg()["category_overrides"].items():
        assert cat in meta()["categories"], cat
        if "block_min" in o:
            assert o["block_min"] > review_min, f"{cat}: block_min would erase the review band"


def test_floor_router_and_fuse_are_consistent():
    c = cfg()
    assert 1 <= c["floor"]["rank"] <= 5 and 0 <= c["floor"]["min_score"] <= 100
    r = c["router"]
    assert r["clean_below"] < r["definite_min"]
    assert r["nlp_confident_lo"] < r["nlp_confident_hi"]
    assert abs(sum(c["fuse"]["weights"].values()) - 1.0) < 1e-9
```

- [ ] **Step 3: Run to verify failure**

Run: `pytest tests/test_context.py tests/test_scoring.py -v`
Expected: FAIL (missing files / schemas).

- [ ] **Step 4: Write schemas**

`schemas/context.schema.json`:
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "context/<lang>.yml",
  "type": "object",
  "additionalProperties": false,
  "required": ["lang", "rules"],
  "properties": {
    "lang": {"type": "string", "pattern": "^[a-z]{2,3}(-[a-z]{4})?$"},
    "rules": {
      "type": "array", "minItems": 1,
      "items": {
        "type": "object", "additionalProperties": false,
        "required": ["id", "type", "terms", "adjust"],
        "properties": {
          "id": {"type": "string", "pattern": "^[a-z][a-z0-9_]*$"},
          "type": {"enum": ["negation", "quotation", "news_report", "target_person", "imperative"]},
          "terms": {"type": "array", "minItems": 1, "items": {"type": "string", "minLength": 1}},
          "adjust": {"type": "integer", "minimum": -50, "maximum": 50}
        }
      }
    }
  }
}
```

`schemas/scoring.schema.json`:
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "scoring/scoring.yml",
  "type": "object",
  "additionalProperties": false,
  "required": ["version", "rank_weight", "corroboration", "fuse", "floor", "thresholds", "category_overrides", "router"],
  "properties": {
    "version": {"type": "integer", "minimum": 1},
    "rank_weight": {"type": "array", "minItems": 5, "maxItems": 5, "items": {"type": "integer", "minimum": 0, "maximum": 100}},
    "corroboration": {
      "type": "object", "additionalProperties": false, "required": ["step", "cap"],
      "properties": {"step": {"type": "integer", "minimum": 0}, "cap": {"type": "integer", "minimum": 0}}
    },
    "fuse": {
      "type": "object", "additionalProperties": false, "required": ["method", "weights"],
      "properties": {
        "method": {"enum": ["max", "weighted"]},
        "weights": {
          "type": "object", "additionalProperties": false, "required": ["stage1", "nlp", "llm"],
          "properties": {
            "stage1": {"type": "number", "minimum": 0, "maximum": 1},
            "nlp": {"type": "number", "minimum": 0, "maximum": 1},
            "llm": {"type": "number", "minimum": 0, "maximum": 1}
          }
        }
      }
    },
    "floor": {
      "type": "object", "additionalProperties": false, "required": ["rank", "min_score"],
      "properties": {"rank": {"type": "integer", "minimum": 1, "maximum": 5}, "min_score": {"type": "integer", "minimum": 0, "maximum": 100}}
    },
    "thresholds": {
      "type": "array", "minItems": 1,
      "items": {
        "type": "object", "additionalProperties": false, "required": ["min", "label", "action"],
        "properties": {
          "min": {"type": "integer", "minimum": 0, "maximum": 100},
          "label": {"enum": ["definite", "probable", "possible", "clean"]},
          "action": {"enum": ["block", "review", "flag", "pass"]}
        }
      }
    },
    "category_overrides": {
      "type": "object",
      "additionalProperties": {
        "type": "object", "additionalProperties": false,
        "properties": {
          "block_min": {"type": "integer", "minimum": 0, "maximum": 100},
          "floor_min_score": {"type": "integer", "minimum": 0, "maximum": 100}
        }
      }
    },
    "router": {
      "type": "object", "additionalProperties": false,
      "required": ["definite_min", "clean_below", "nlp_confident_hi", "nlp_confident_lo"],
      "properties": {
        "definite_min": {"type": "integer", "minimum": 0, "maximum": 100},
        "clean_below": {"type": "integer", "minimum": 0, "maximum": 100},
        "nlp_confident_hi": {"type": "integer", "minimum": 0, "maximum": 100},
        "nlp_confident_lo": {"type": "integer", "minimum": 0, "maximum": 100}
      }
    }
  }
}
```

- [ ] **Step 5: Write data**

`scoring/scoring.yml`:
```yaml
version: 1
# lexicon_score = max over matched entries of rank_weight[rank-1] * (1 - ambiguity)
rank_weight: [20, 40, 60, 80, 100]
# corroboration = min((distinct matched entries of the same concept - 1) * step, cap)
corroboration: {step: 10, cap: 20}
fuse:
  method: max          # max | weighted
  weights: {stage1: 0.4, nlp: 0.3, llm: 0.3}
# A matched entry with rank >= floor.rank keeps final_score >= floor.min_score.
floor: {rank: 5, min_score: 60}
thresholds:           # evaluated top to bottom, first match wins
  - {min: 85, label: definite, action: block}
  - {min: 60, label: probable, action: review}
  - {min: 35, label: possible, action: flag}
  - {min: 0, label: clean, action: pass}
category_overrides:
  illegal: {block_min: 70}
  defamation: {block_min: 90}
router:
  definite_min: 85
  clean_below: 20
  nlp_confident_hi: 80
  nlp_confident_lo: 20
```

`context/en.yml`:
```yaml
lang: en
rules:
  - {id: en_news_report, type: news_report, terms: [reported, according to, allegedly], adjust: -15}
```
`context/ko.yml`:
```yaml
lang: ko
rules:
  - {id: ko_news_report, type: news_report, terms: [보도, 에 따르면], adjust: -15}
```
`context/ja.yml`:
```yaml
lang: ja
rules:
  - {id: ja_news_report, type: news_report, terms: [報道, によると], adjust: -15}
```
`context/zh-hans.yml`:
```yaml
lang: zh-hans
rules:
  - {id: zh_hans_news_report, type: news_report, terms: [据报道, 根据], adjust: -15}
```
`context/zh-hant.yml`:
```yaml
lang: zh-hant
rules:
  - {id: zh_hant_news_report, type: news_report, terms: [據報導, 根據], adjust: -15}
```

- [ ] **Step 6: Run to verify pass**

Run: `pytest -q`
Expected: all PASS.

- [ ] **Step 7: Commit**

```bash
git add schemas context scoring tests
git commit -m "feat: add context rules and scoring configuration with consistency tests"
```

---

### Task 6: Stage contracts, LLM prompt/output schema, model registry

**Files:**
- Create: `schemas/{nlp_request,nlp_result,llm_request,llm_verdict,detection,models}.schema.json`
- Create: `llm/output_schema.json`, `llm/prompts/fraud.en.md`, `models/registry.yml`
- Modify: `tests/schema_map.py`
- Test: `tests/test_models.py`, `tests/test_contracts.py`

**Interfaces:**
- Consumes: `helpers`, `meta()["languages"]`, `meta()["schema_version"]`.
- Produces: contract schemas (filenames above); `models/registry.yml` shape `{schema_version, models: {<id>: {kind, stage, lang[], hf_repo, revision, sha256, format, input_contract, output_contract, prompt_template, min_schema_version, trained_on, status}}}`; prompt files `llm/prompts/<category>.<lang>.md` with YAML front matter `id, version, category, lang, output_schema`.

- [ ] **Step 1: Append to `tests/schema_map.py`**

```python
GLOBS += [
    ("models/registry.yml", "models"),
]
```

- [ ] **Step 2: Write the failing tests**

`tests/test_models.py`:
```python
import re

import pytest
import yaml

from helpers import ROOT, load_yaml, meta, read_text, rel

PINNED_FORBIDDEN = {"main", "master", "HEAD", ""}


def models():
    return load_yaml(ROOT / "models" / "registry.yml")["models"]


@pytest.mark.parametrize("model_id,m", sorted(models().items()))
def test_model_entry_rules(model_id, m):
    assert model_id.startswith(m["kind"] + "."), f"{model_id}: id must start with kind"
    assert m["stage"] == (2 if m["kind"] == "nlp" else 3)
    assert set(m["lang"]) <= set(meta()["languages"])
    assert m["min_schema_version"] <= meta()["schema_version"]
    for key in ("input_contract", "output_contract"):
        assert (ROOT / m[key]).exists(), f"{model_id}: {key} {m[key]} does not exist"
    if m["sha256"] is not None:
        assert re.fullmatch(r"[0-9a-f]{64}", m["sha256"])
    if m["kind"] == "nlp":
        assert m["prompt_template"] is None
    if m["prompt_template"] is not None:
        assert (ROOT / "llm" / "prompts" / f"{m['prompt_template']}.md").exists()
    if m["status"] in ("experimental", "stable"):
        assert m["hf_repo"], f"{model_id}: {m['status']} model needs hf_repo"
        assert m["revision"] not in PINNED_FORBIDDEN and m["revision"] is not None, (
            f"{model_id}: revision must be pinned, not a branch name"
        )


@pytest.mark.parametrize("path", sorted((ROOT / "llm" / "prompts").glob("*.md")), ids=rel)
def test_prompt_templates(path):
    _, front, body = read_text(path).split("---", 2)
    fm = yaml.safe_load(front)
    category, lang = path.stem.split(".", 1)
    assert fm["id"] == path.stem
    assert fm["category"] == category and category in meta()["categories"]
    assert fm["lang"] == lang and lang in meta()["languages"]
    assert isinstance(fm["version"], int) and fm["version"] >= 1
    assert (ROOT / fm["output_schema"]).exists()
    assert "{{text}}" in body
```

`tests/test_contracts.py`:
```python
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
```
Note: `detection.span` ordering (`[3, 1]`) cannot be expressed in JSON Schema, so that INVALID case fails through `action: "shout"`; ordering is checked in the eval task for gold data and is an engine responsibility.

- [ ] **Step 3: Run to verify failure**

Run: `pytest tests/test_models.py tests/test_contracts.py -v`
Expected: FAIL (missing schemas, registry, output schema, prompt).

- [ ] **Step 4: Write contract schemas**

`schemas/nlp_request.schema.json`:
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "NLP stage request",
  "type": "object", "additionalProperties": false,
  "required": ["text", "lang", "spans"],
  "properties": {
    "text": {"type": "string"},
    "lang": {"enum": ["en", "ko", "ja", "zh-hans", "zh-hant"]},
    "spans": {
      "type": "array",
      "items": {
        "type": "object", "additionalProperties": false, "required": ["span", "concept"],
        "properties": {
          "span": {"type": "array", "minItems": 2, "maxItems": 2, "items": {"type": "integer", "minimum": 0}},
          "concept": {"type": "integer", "minimum": 1000, "maximum": 9999}
        }
      }
    }
  }
}
```

`schemas/nlp_result.schema.json`:
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "NLP stage result",
  "type": "object", "additionalProperties": false,
  "required": ["score", "signals"],
  "properties": {
    "score": {"type": "number", "minimum": 0, "maximum": 100},
    "signals": {
      "type": "object", "additionalProperties": false,
      "properties": {
        "negation": {"type": "boolean"},
        "quotation": {"type": "boolean"},
        "target_person": {"type": "boolean"},
        "intent": {"type": "string", "minLength": 1},
        "sentiment": {"type": "number", "minimum": -1, "maximum": 1}
      }
    }
  }
}
```

`schemas/llm_request.schema.json`:
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "LLM stage request",
  "type": "object", "additionalProperties": false,
  "required": ["text", "lang", "spans", "prompt_template_id"],
  "properties": {
    "text": {"type": "string"},
    "lang": {"enum": ["en", "ko", "ja", "zh-hans", "zh-hant"]},
    "spans": {
      "type": "array",
      "items": {
        "type": "object", "additionalProperties": false, "required": ["span", "concept"],
        "properties": {
          "span": {"type": "array", "minItems": 2, "maxItems": 2, "items": {"type": "integer", "minimum": 0}},
          "concept": {"type": "integer", "minimum": 1000, "maximum": 9999}
        }
      }
    },
    "prompt_template_id": {"type": "string", "pattern": "^[a-z_]+\\.[a-z0-9-]+$"}
  }
}
```

`schemas/llm_verdict.schema.json`:
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "LLM stage verdict",
  "type": "object", "additionalProperties": false,
  "required": ["scores", "label", "model_id", "prompt_version"],
  "properties": {
    "scores": {
      "type": "object", "minProperties": 1,
      "additionalProperties": {"type": "number", "minimum": 0, "maximum": 100}
    },
    "label": {"enum": ["definite", "probable", "possible", "clean"]},
    "rationale": {"type": "string"},
    "model_id": {"type": "string", "minLength": 1},
    "prompt_version": {"type": "integer", "minimum": 1}
  }
}
```

`schemas/detection.schema.json`:
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Detection record shared by all stages",
  "type": "object", "additionalProperties": false,
  "required": ["span", "concept", "category", "score", "label", "action", "stage_reached", "matched_entry_ids"],
  "properties": {
    "span": {"type": "array", "minItems": 2, "maxItems": 2, "items": {"type": "integer", "minimum": 0}},
    "concept": {"type": "integer", "minimum": 1000, "maximum": 9999},
    "category": {"enum": ["defamation", "hate", "fraud", "illegal", "cross_cutting"]},
    "score": {"type": "number", "minimum": 0, "maximum": 100},
    "label": {"enum": ["definite", "probable", "possible", "clean"]},
    "action": {"enum": ["block", "review", "flag", "pass"]},
    "stage_reached": {"enum": [1, 2, 3]},
    "matched_entry_ids": {"type": "array", "items": {"type": "string"}},
    "signals": {"type": "object"}
  }
}
```

`schemas/models.schema.json`:
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "models/registry.yml",
  "type": "object", "additionalProperties": false,
  "required": ["schema_version", "models"],
  "properties": {
    "schema_version": {"type": "integer", "minimum": 1},
    "models": {
      "type": "object", "minProperties": 1,
      "propertyNames": {"pattern": "^(nlp|llm)\\.[a-z0-9_.-]+$"},
      "additionalProperties": {
        "type": "object", "additionalProperties": false,
        "required": ["kind", "stage", "lang", "hf_repo", "revision", "sha256", "format", "input_contract", "output_contract", "prompt_template", "min_schema_version", "trained_on", "status"],
        "properties": {
          "kind": {"enum": ["nlp", "llm"]},
          "stage": {"enum": [2, 3]},
          "lang": {"type": "array", "minItems": 1, "items": {"enum": ["en", "ko", "ja", "zh-hans", "zh-hant"]}},
          "hf_repo": {"type": ["string", "null"]},
          "revision": {"type": ["string", "null"]},
          "sha256": {"type": ["string", "null"]},
          "format": {"enum": ["onnx", "safetensors", "gguf"]},
          "input_contract": {"type": "string"},
          "output_contract": {"type": "string"},
          "prompt_template": {"type": ["string", "null"]},
          "min_schema_version": {"type": "integer", "minimum": 1},
          "trained_on": {"type": ["string", "null"]},
          "status": {"enum": ["planned", "experimental", "stable"]}
        }
      }
    }
  }
}
```

- [ ] **Step 5: Write `llm/output_schema.json`, prompt, and model registry**

`llm/output_schema.json`:
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Constrained-decoding output for small LLM judges",
  "type": "object", "additionalProperties": false,
  "required": ["scores", "label"],
  "properties": {
    "scores": {
      "type": "object", "additionalProperties": false,
      "required": ["defamation", "hate", "fraud", "illegal"],
      "properties": {
        "defamation": {"type": "integer", "minimum": 0, "maximum": 100},
        "hate": {"type": "integer", "minimum": 0, "maximum": 100},
        "fraud": {"type": "integer", "minimum": 0, "maximum": 100},
        "illegal": {"type": "integer", "minimum": 0, "maximum": 100}
      }
    },
    "label": {"enum": ["definite", "probable", "possible", "clean"]},
    "rationale": {"type": "string", "maxLength": 300}
  }
}
```
(`test_llm_output_schema_is_valid_and_covers_all_categories` reads `properties.scores.required`, so the `required` list lives inside `scores` as shown.)

`llm/prompts/fraud.en.md`:
```markdown
---
id: fraud.en
version: 1
category: fraud
lang: en
output_schema: llm/output_schema.json
---
You are a content-safety classifier. Decide whether the text below actually
promotes or attempts fraud, as opposed to reporting on it, quoting it, negating
it, or joking.

Text: {{text}}

Matched spans: {{spans}}

Respond with JSON only, matching the output schema. Scores are 0-100 per category.
```

`models/registry.yml`:
```yaml
schema_version: 1
models:
  nlp.context.ko:
    kind: nlp
    stage: 2
    lang: [ko]
    hf_repo: null
    revision: null
    sha256: null
    format: onnx
    input_contract: schemas/nlp_request.schema.json
    output_contract: schemas/nlp_result.schema.json
    prompt_template: null
    min_schema_version: 1
    trained_on: null
    status: planned
  llm.judge.fraud.en:
    kind: llm
    stage: 3
    lang: [en]
    hf_repo: null
    revision: null
    sha256: null
    format: gguf
    input_contract: schemas/llm_request.schema.json
    output_contract: schemas/llm_verdict.schema.json
    prompt_template: fraud.en
    min_schema_version: 1
    trained_on: null
    status: planned
```

- [ ] **Step 6: Run to verify pass**

Run: `pytest -q`
Expected: all PASS.

- [ ] **Step 7: Commit**

```bash
git add schemas llm models tests
git commit -m "feat: add stage contracts, LLM prompt/output schema and model registry"
```

---

### Task 7: Evaluation schema, gold set, metrics definition

**Files:**
- Create: `schemas/eval_sample.schema.json`, `eval/gold/gold.jsonl`, `eval/METRICS.md`
- Test: `tests/test_eval.py`

**Interfaces:**
- Consumes: `helpers`, `registry()`, `meta()`.
- Produces: JSONL sample shape `{text, lang, labels[{concept, span[start,end]}], source, license}`; spans are **Unicode code point** offsets, `0 <= start < end <= len(text)`.

- [ ] **Step 1: Write the failing test `tests/test_eval.py`**

```python
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
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/test_eval.py -v`
Expected: FAIL (`FileNotFoundError: eval/gold/gold.jsonl`).

- [ ] **Step 3: Write schema, gold set and metrics doc**

`schemas/eval_sample.schema.json`:
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "eval sample (one JSON object per line)",
  "type": "object", "additionalProperties": false,
  "required": ["text", "lang", "labels", "source", "license"],
  "properties": {
    "text": {"type": "string", "minLength": 1},
    "lang": {"enum": ["en", "ko", "ja", "zh-hans", "zh-hant"]},
    "labels": {
      "type": "array",
      "items": {
        "type": "object", "additionalProperties": false, "required": ["concept", "span"],
        "properties": {
          "concept": {"type": "integer", "minimum": 1000, "maximum": 9999},
          "span": {"type": "array", "minItems": 2, "maxItems": 2, "items": {"type": "integer", "minimum": 0}}
        }
      }
    },
    "source": {"type": "string", "minLength": 1},
    "license": {"type": "string", "minLength": 1}
  }
}
```

`eval/gold/gold.jsonl` (one JSON object per line, no trailing blank line issues):
```
{"text": "Join now for guaranteed returns on your deposit.", "lang": "en", "labels": [{"concept": 3001, "span": [13, 31]}], "source": "synthetic", "license": "CC0-1.0"}
{"text": "지금 가입하면 원금보장 수익!", "lang": "ko", "labels": [{"concept": 3001, "span": [8, 12]}], "source": "synthetic", "license": "CC0-1.0"}
{"text": "元本保証の投資案件です", "lang": "ja", "labels": [{"concept": 3001, "span": [0, 4]}], "source": "synthetic", "license": "CC0-1.0"}
{"text": "这个项目稳赚不赔，快来投资", "lang": "zh-hans", "labels": [{"concept": 3001, "span": [4, 8]}], "source": "synthetic", "license": "CC0-1.0"}
{"text": "這個項目穩賺不賠，快來投資", "lang": "zh-hant", "labels": [{"concept": 3001, "span": [4, 8]}], "source": "synthetic", "license": "CC0-1.0"}
{"text": "Thanks for the update, see you tomorrow.", "lang": "en", "labels": [], "source": "synthetic", "license": "CC0-1.0"}
```

`eval/METRICS.md`:
```markdown
# Evaluation metrics

The gold set in `eval/gold/` is a sanity check only. Large corpora live in the
training repository.

- **Unit:** a label is `(concept, span)`; spans are Unicode code point offsets,
  half-open `[start, end)`.
- **Match:** a predicted detection matches a gold label when the concepts are
  equal and the spans overlap by at least 50% of the shorter span.
- **Precision / recall / F1** are reported per category x language.
- **Stage resolution:** the share of samples whose final decision was made at
  stage 1, 2 or 3 (`stage_reached` in the detection record).
- **Ambiguity refresh:** for each lexicon entry, `1 - precision` over the
  samples where it fires is the suggested new `ambiguity` value; update the
  lexicon by hand after review.
```

- [ ] **Step 4: Run to verify pass**

Run: `pytest -q`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add schemas/eval_sample.schema.json eval tests/test_eval.py
git commit -m "feat: add eval sample schema, gold set and metrics definition"
```

---

### Task 8: INTEGRATION.md, CI, final verification

**Files:**
- Create: `INTEGRATION.md`, `.github/workflows/tests.yml`
- Modify: `README.md` (layout section)

**Interfaces:**
- Consumes: everything above; documents it.

- [ ] **Step 1: Write `INTEGRATION.md`**

```markdown
# Integration Guide: building an engine on this data

This repository is **data and contracts**, not a runnable detector. An engine
(for example the future `tnscrop` package) loads this data and implements the
pipeline below. Contracts are JSON Schema in `schemas/`; any language can
implement them.

## Versions
- `reference/meta.yml`: `schema_version` (contract version) and `data_version`.
- An engine declares the `schema_version` range it supports and refuses data
  outside it. Adding terms bumps only `data_version`.

## Pipeline
    text -> normalize -> prefilter -> lexicon match -> score1
       |- score1 >= router.definite_min AND no ambiguous/requires_context hit -> DONE
       |- score1 < router.clean_below AND no hit                              -> DONE (clean)
       '- else -> NLP stage -> score2
            |- score2 >= nlp_confident_hi or <= nlp_confident_lo -> DONE
            '- uncertain band -> LLM stage -> score3 -> DONE
NLP and LLM stages are optional; without them report `stage_reached: 1`.

## What to implement
1. **Load** `lexicon/**`, `normalize/<lang>.yml`, `context/<lang>.yml`,
   `stopwords/<lang>.yml`, `scoring/scoring.yml`, `reference/registry.yml`.
2. **Normalize** per language, applying rules in file order (`strip`, `map`,
   `strip_between`, `nfkc`, `collapse_repeats`). Keep an offset map so matches
   are reported against the original text. `normalize/*.yml` fixtures are your
   conformance tests. Recommendation: match `lang: und` regex entries against
   the text *before* `strip`/`map` rules, because digit substitutions (e.g.
   `1 -> i`) would corrupt digit-run patterns.
3. **Prefilter** with an Aho-Corasick automaton over `hit_keywords` and literal
   terms. A regex entry with `always_run: true` and no `hit_keywords` must
   always run.
4. **Match** literals/phrases (honor `flags`) and regexes with an RE2-compatible
   engine.
5. **Score** with `scoring/scoring.yml`:
   `lexicon_score = max(rank_weight[rank-1] * (1 - ambiguity))`;
   `corroboration = min((distinct matched entries of the same concept - 1) * step, cap)`;
   `stage1 = clamp(lexicon_score + corroboration + sum(context adjustments), 0, 100)`.
   Entries with `requires_context: true` are never decisive alone: route them
   to the NLP stage. A matched entry with `rank >= floor.rank` keeps
   `final_score >= floor.min_score` regardless of later stages.
6. **Decide** with `thresholds` (first match wins); apply `category_overrides.block_min`.
7. **Emit** records matching `schemas/detection.schema.json`. Log codes and
   spans, not raw text.

## Model stages
`models/registry.yml` holds pointers only. Resolve `hf_repo` at `revision`
(never a branch), verify `sha256` when present, and validate requests/results
against the entry's `input_contract`/`output_contract`. LLM prompts live in
`llm/prompts/<category>.<lang>.md`; constrain decoding with
`llm/output_schema.json`.

## Conformance checklist
- Passes all `normalize/*.yml` fixtures.
- Produces detections that validate against `schemas/detection.schema.json`.
- Reproduces the gold set in `eval/gold/` (see `eval/METRICS.md`).
```

- [ ] **Step 2: Write `.github/workflows/tests.yml`**

```yaml
name: tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -e ".[test,re2]"
      - run: pytest -q
```

- [ ] **Step 3: Append a layout section to `README.md`**

```markdown
## Layout

    lexicon/     words, phrases and regexes per category and language
    normalize/   evasion-normalization rules with fixtures
    context/     score-adjusting context rules
    stopwords/   per-language stopwords
    scoring/     scoring formula parameters, thresholds, routing
    reference/   stable concept codes (append-only)
    models/      pointers to NLP/LLM models on Hugging Face
    llm/         prompt templates and constrained-output schema
    schemas/     JSON Schema contracts
    eval/        sample schema, gold set, metrics definition
    tests/       data-integrity tests
```

- [ ] **Step 4: Run the full suite and read the output**

Run: `pytest -q -W default 2>&1 | tail -20`
Expected: all tests PASS; one `UserWarning: coverage gaps: ...` from `test_language_coverage_report` (expected for the seed set). Report the actual pass count in the hand-off.

- [ ] **Step 5: Commit**

```bash
git add INTEGRATION.md .github README.md
git commit -m "docs: add integration guide and CI workflow"
```

---

## Self-Review

**Spec coverage:** sections 1/2 (scope, layout) → Tasks 1-8; 3 (registry) → Task 2; 4 (lexicon schema) → Task 3; 5 (normalization, 5 languages, no cross-script folding) → Task 4; 6 (scoring, floor rule, thresholds, overrides, routing) → Task 5 plus `INTEGRATION.md`; 7 (contracts, prompts, output schema, detection record) → Task 6; 8 (model registry rules) → Task 6; 9 (integrity tests) → Tasks 1-7; 10 (eval) → Task 7; 11 (versioning) → Task 1 (`meta.yml`, pyproject check) and Task 8. Gaps by design: `scoring/weights/` (see deviation note), ambiguity recomputation (documented in METRICS.md, manual).

**Placeholder scan:** none found; all steps contain complete content.

**Type consistency:** `registry()` returns the `codes` map everywhere; `lexicon_entries()` yields `(path, doc, entry)` everywhere; `normalize()/rules_for()` signatures match between Task 4 files; concept names carry the category prefix in the registry and category files; the contract `lang` enums are checked against `meta.yml`.

**Known judgment calls to confirm:** the contact-redirect regex and en leetspeak interaction (INTEGRATION.md recommends matching `und` regexes before `map` rules); seed lexicon is intentionally tiny (1 entry per category/language) and avoids slurs: real term lists are a content task for a policy owner.
