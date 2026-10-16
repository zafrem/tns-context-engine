# tns-context-engine

Data and specification foundation for filtering **defamation, hate, fraud and
illegal** content in English, Korean, Japanese and Chinese (Simplified and
Traditional). Modeled on [`pii-pattern-engine`](https://github.com/zafrem/pii-pattern-engine):
declarative YAML data, stable numeric codes, a documented integration contract
and data-integrity tests.

It ranks words and phrases and defines the contracts for plugging in NLP and
small-LLM stages. It contains **no runtime engine and no model weights**: the
engine (planned as `tnscrop`), training data and models live elsewhere, and
`models/` only holds pointers to Hugging Face.

Languages (lowercase BCP 47): `en`, `ko`, `ja`, `zh-hans`, `zh-hant`.

## Status

Foundation release (`data_version` 0.1.0). The structure, schemas, contracts and
integrity tests are complete. The lexicon now has a first **draft** across all
four categories (defamation, hate, fraud and illegal) and cross-cutting patterns
(about 680 entries across all five languages; drafts awaiting native-speaker and
policy review), and rank and ambiguity values are uncalibrated.
See "Open items" in
`docs/superpowers/specs/2026-10-16-tns-context-engine-design.md`.

## How it works

An engine implementing `INTEGRATION.md` runs this pipeline, stopping as soon as
a stage is confident:

    text -> normalize -> prefilter -> lexicon match -> score
         -> (uncertain) NLP stage -> (still uncertain) small-LLM stage -> action

- **Rank and ambiguity.** Every lexicon entry has a severity `rank` (1-5) and an
  `ambiguity` (0-1, how often the term is benign). Scores use
  `rank_weight[rank] * (1 - ambiguity)`, with context rules adjusting the result.
- **Actions.** `block | review | flag | pass`, with per-category thresholds.
  Severe (rank 5) matches keep a minimum score even if a later stage disagrees.
- **Concept codes.** Each concept has a stable, append-only code shared by all
  languages:

  | Series | Category |
  |---|---|
  | 1xxx | defamation |
  | 2xxx | hate |
  | 3xxx | fraud |
  | 4xxx | illegal |
  | 9xxx | cross-cutting (obfuscation, contact redirection) |

## Layout

    lexicon/     words, phrases and regexes per category and language
    normalize/   evasion-normalization rules with fixtures
    context/     score-adjusting context rules
    stopwords/   per-language stopwords
    scoring/     scoring formula parameters, thresholds, routing
    reference/   stable concept codes (append-only), meta.yml (versions, languages)
    models/      pointers to NLP/LLM models on Hugging Face
    llm/         prompt templates and constrained-output schema
    schemas/     JSON Schema contracts
    eval/        sample schema, gold set, metrics definition
    tests/       data-integrity tests
    docs/        design spec

## Using it as a submodule

This repository is not packaged. Add it to an engine repo with
`git submodule add https://github.com/zafrem/tns-context-engine tns-context-engine`,
pin the commit or tag you tested against, and read the files directly (see
`INTEGRATION.md`). Check `schema_version` in `reference/meta.yml` before loading:
adding terms bumps only `data_version`; breaking contract changes bump
`schema_version`.

## Contributing data

1. Pick the file: `lexicon/<category>/<lang>.yml` (regexes go in `lexicon/patterns/`).
2. Write the term in already-normalized form and give it a registered `concept`,
   a `rank` and an `ambiguity`. Set `requires_context: true` for terms that are
   never decisive alone.
3. Write non-printing or invisible characters as `\uXXXX` escapes; use lowercase
   language tags and `.yml` extensions.
4. Run the tests. New concepts go in `reference/<category>.yml` and
   `reference/registry.yml`, and codes are never reused or renumbered.

## Tests

    python3 -m venv .venv && . .venv/bin/activate
    pip install -r requirements-test.txt
    pytest -q

The suite is data-only. It checks schema conformance for every file, unique and
append-only codes, referential integrity, lexicon quality (normalized terms, no
duplicates or stopwords), RE2-safe regexes (authoritative when `google-re2` is
installed), normalizer fixtures, scoring consistency, the model registry (never
downloads models) and eval spans. A language-coverage warning at the end of the
run is expected until every concept has entries in all five languages.

## Releasing

Concept codes are append-only. When cutting a release, copy the current
`reference/registry.yml` over `reference/released.yml` (keep `version`), bump
`data_version` in `reference/meta.yml`, and tag the commit.
`test_codes_are_append_only_against_released_snapshot` then guards every later
change; review any edit to `released.yml` as a breaking change.
