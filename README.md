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
