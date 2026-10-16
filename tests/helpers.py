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
