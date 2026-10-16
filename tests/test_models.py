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
