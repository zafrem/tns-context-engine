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
