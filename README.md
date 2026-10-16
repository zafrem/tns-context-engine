# tns-context-engine

Data and specification foundation for filtering defamation, hate, fraud and
illegal content in English, Korean, Japanese and Chinese (Simplified and
Traditional). Modeled on `pii-pattern-engine`.

This repository contains data, JSON Schema contracts, a model registry (pointers
to Hugging Face only) and data-integrity tests. It contains **no runtime engine
and no model weights**. See `INTEGRATION.md` for the contract an engine must
implement and `docs/superpowers/specs/` for the design.

Languages (lowercase BCP 47): `en`, `ko`, `ja`, `zh-hans`, `zh-hant`.

## Using it as a submodule

This repository is not packaged. Add it to an engine repo with
`git submodule add <url> tns-context-engine`, pin the commit or tag you
tested against, and read the files directly (see `INTEGRATION.md`). Check
`schema_version` in `reference/meta.yml` before loading.

## Tests

    python3 -m venv .venv && . .venv/bin/activate
    pip install -r requirements-test.txt
    pytest -q

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

## Releasing

Concept codes are append-only. When cutting a release, copy the current
`reference/registry.yml` over `reference/released.yml` (keep `version`), bump
`data_version` in `reference/meta.yml`, and tag the commit.
`test_codes_are_append_only_against_released_snapshot` then guards every later
change; review any edit to `released.yml` as a breaking change.
