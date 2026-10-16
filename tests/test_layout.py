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
