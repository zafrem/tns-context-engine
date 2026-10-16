# tns-context-engine — Design Spec

Date: 2026-10-16
Status: Draft for review

## 1. Purpose and scope

`tns-context-engine` is a **data and specification foundation** for filtering
defamation, hate, fraud and illegal content in **English, Korean, Japanese and
Chinese (Simplified and Traditional)** text. It follows the philosophy of
`pii-pattern-engine`: declarative YAML data, stable numeric codes, a documented
integration contract, and data-integrity tests.

Language tags are BCP 47 subtags written in **lowercase** everywhere (file names,
`lang` fields, registry keys): `en`, `ko`, `ja`, `zh-hans`, `zh-hant`. A test
rejects any other casing.

It ranks words and phrases, and defines the contracts for plugging in NLP and
small-LLM stages. It contains **no runtime engine and no model weights**.

### In this repository
- Lexicon, normalization rules, context rules, stopwords
- Scoring configuration and routing thresholds
- Stable code registry
- JSON Schemas for every file type and for stage inputs/outputs (`schemas/`)
- LLM prompt templates and output schema
- Model registry (pointers only) for NLP/LLM models hosted on Hugging Face
- Evaluation dataset schema and a small gold set
- Data-integrity tests (`pytest`, data-only)
- `INTEGRATION.md`: the contract any engine must implement

### Out of scope (lives elsewhere)
- The `tnscrop` engine package (does not exist yet)
- Training data and training code (separate repository)
- NLP/LLM model weights (Hugging Face)
- Model serving or adapter code

### Success criteria
- An engine author can implement a compliant detector from `schemas/` and
  `INTEGRATION.md` alone, in any language.
- A data-only change (new terms) never requires an engine change.
- CI fails on any data inconsistency (see section 9).

## 2. Repository layout

```
tns-context-engine/
├── lexicon/
│   ├── defamation/{en,ko,ja,zh-hans,zh-hant}.yml
│   ├── hate/{en,ko,ja,zh-hans,zh-hant}.yml
│   ├── fraud/{en,ko,ja,zh-hans,zh-hant}.yml
│   ├── illegal/{en,ko,ja,zh-hans,zh-hant}.yml
│   └── patterns/*.yml            # regex entries (obfuscation, contact redirection, ...)
├── normalize/{en,ko,ja,zh-hans,zh-hant}.yml   # pre-match normalization rules + fixtures
├── context/{en,ko,ja,zh-hans,zh-hant}.yml     # score-adjusting context rules
├── stopwords/{en,ko,ja,zh-hans,zh-hant}.yml
├── scoring/
│   ├── scoring.yml               # formula parameters, thresholds, routing
│   └── weights/<category>.yml    # per-category overrides
├── reference/
│   ├── registry.yml              # master code map
│   └── <category>.yml            # concept details
├── models/
│   └── registry.yml              # pointers to HF-hosted NLP/LLM models
├── llm/
│   ├── prompts/<category>.<lang>.md
│   └── output_schema.json
├── schemas/                      # JSON Schema contracts
├── eval/                         # dataset schema + gold set
├── tests/                        # data-integrity tests only
├── docs/superpowers/specs/
├── INTEGRATION.md
├── requirements-test.txt         # test dependencies only (not packaged; used as a git submodule)
└── README.md
```

Data is organized **category first, language second** (`lexicon/<category>/<lang>.yml`),
because policy and review ownership follow categories, and adding a language
means adding one file per category.

## 3. Code registry (`reference/`)

Codes identify **concepts**, not languages. The same concept has entries in
several languages and shares one code, so logs and policies are language-neutral.

| Series | Category | Examples |
|---|---|---|
| 1xxx | defamation | 1001 insult, 1002 false_accusation, 1003 doxxing_threat |
| 2xxx | hate | 2001 slur_ethnic, 2002 slur_gender, 2003 slur_religion, 2004 slur_disability |
| 3xxx | fraud | 3001 investment_scam, 3002 phishing, 3003 romance_scam, 3004 impersonation |
| 4xxx | illegal | 4001 drugs, 4002 weapons, 4003 illegal_gambling, 4004 csam_solicitation |
| 9xxx | cross-cutting | 9001 obfuscation_marker, 9002 contact_redirect |

Rules:
- `reference/registry.yml` is the master flat map `name: code`; per-category
  files hold descriptions and `rank_default`.
- Codes are **append-only and never reused**. Deprecated concepts stay in the
  registry with `deprecated: true`.
- Example codes above are an initial seed; the final concept list is part of
  implementation, subject to review.

## 4. Lexicon entry schema (`lexicon/<category>/<lang>.yml`)

```yaml
namespace: fraud.ko
lang: ko
entries:
  - id: fraud_ko_0001          # stable, unique across the repo
    concept: 3001              # registry code
    term: "원금보장"
    type: literal              # literal | phrase | regex
    rank: 4                    # 1-5 severity of the concept when truly used
    ambiguity: 0.2             # 0-1, how often the term is benign
    requires_context: false    # true: never decisive alone, always routed to NLP
    flags: []                  # IGNORECASE, WORD_BOUNDARY
    hit_keywords: []           # prefilter anchors; required for type: regex
    notes: ""
```

- `rank` is severity, set by humans from policy. `ambiguity` is false-positive
  risk and may be recomputed from eval results. They are kept separate so the
  scorer can weigh both.
- Terms are written in normalized form (section 5). `type: regex` is limited to
  the RE2 subset (no backreferences, no lookaround) so any engine can match in
  linear time.
- A pattern entry with no `hit_keywords` must always run (same rule as PII).

## 5. Normalization (`normalize/<lang>.yml`)

Applied before matching. The engine must return matches against the original
text via an offset map. Each rule file carries `fixtures` (input → expected output).

| Lang | Rules |
|---|---|
| en | leetspeak, zero-width characters, homoglyphs, repeated-character collapse |
| ko | jamo decomposition/composition, choseong-only forms, inserted symbols/spaces, hanja/romanization |
| ja | NFKC (full/half width), hiragana↔katakana folding, kanji variants, inserted symbols |
| zh-hans | pinyin/initialism evasion, homophone substitution, symbol insertion, variant-character substitution |
| zh-hant | Zhuyin/pinyin initialism evasion, homophone substitution, symbol insertion, variant-character substitution |

Simplified and Traditional are separate language tags with separate rule files
and lexicons, because vocabulary differs by region (mainland, Taiwan, Hong Kong)
and script folding is lossy (one-to-many mappings such as 发 → 發/髮). Folding
across scripts is **not** part of normalization. An engine may optionally match
a text against the other script's lexicon as a fallback after script detection;
that behavior is an engine option and not part of this data contract. Concept
codes are shared, so `zh-hans` and `zh-hant` entries for one concept share a code.

## 6. Scoring and routing (`scoring/`)

```
lexicon_score = max over matched entries of rank_weight[rank] * (1 - ambiguity)   # 0-100
corroboration = min((distinct_matched_entries_same_concept - 1) * step, cap)
context_adj   = sum of fired context rules (negation, quotation, news, target-person,
                imperative; signed)
stage1_score  = clamp(lexicon_score + corroboration + context_adj, 0, 100)
final_score   = fuse(stage1_score, nlp_score?, llm_score?)
```

- `max` rather than PII's average: one strong slur must not be diluted by
  harmless co-occurring words.
- `fuse` is configured in YAML (`max` default, or `weighted`).
- **Floor rule**: when a rank-5 entry matched, `final_score` is never below
  `floor` (default 60, i.e. `review`), even if a later stage scores it benign.
  Configurable per category.

### Thresholds and actions

```yaml
thresholds:
  - { min: 85, label: definite, action: block }
  - { min: 60, label: probable, action: review }
  - { min: 35, label: possible, action: flag }
  - { min: 0,  label: clean,    action: pass }
category_overrides:
  illegal:    { block_min: 70 }
  defamation: { block_min: 90 }
```

The action vocabulary is a closed enum in `schemas/`: `block | review | flag | pass`.
Adding an action (e.g. `mask`) is a schema version bump.

### Stage routing

```
text -> normalize -> prefilter -> lexicon match -> score1
   |- score1 >= definite_min AND no ambiguous/requires_context hit -> DONE
   |- score1 < floor_min AND no hit                                -> DONE (clean)
   '- else -> NLP stage -> score2
        |- confident (>= hi or <= lo) -> DONE
        '- uncertain band -> LLM stage -> score3 -> DONE
```

Router thresholds live in `scoring/scoring.yml`. The NLP and LLM stages are
optional: with neither present, an engine degrades to lexicon + context rules
and reports `stage_reached: 1`.

## 7. Stage contracts (`schemas/`, `llm/`)

Contracts are JSON Schema, language-neutral. No Python protocols are defined here.

- `nlp_request.json` / `nlp_result.json`: text, spans, lang → score (0-100) and
  signals `{negation, quotation, target_person, intent, sentiment}`.
- `llm_request.json` / `llm_verdict.json`: text window, matched spans and
  concepts, lang, `prompt_template_id` → per-category scores, label, optional
  rationale, `model_id`, `prompt_version`.
- `llm/prompts/<category>.<lang>.md`: versioned prompt templates.
- `llm/output_schema.json`: strict schema suitable for constrained decoding by
  a small model.
- `detection.json`: the shared output record.

```json
{ "span": [12, 18], "concept": 3001, "category": "fraud",
  "score": 82, "label": "probable", "action": "review",
  "stage_reached": 2, "matched_entry_ids": ["fraud_ko_0001"],
  "signals": {"negation": false} }
```

Logs and APIs carry codes and spans, not raw text.

## 8. Model registry (`models/registry.yml`) — pointers only

```yaml
schema_version: 1
models:
  nlp.context.ko:
    kind: nlp                      # nlp | llm
    stage: 2
    lang: [ko]
    hf_repo: "<org>/<name>"        # may be empty while status is planned
    revision: "<commit sha or tag>" # pinned, never 'main'
    sha256: "<digest>"             # optional
    format: onnx                   # onnx | safetensors | gguf ...
    input_contract: schemas/nlp_request.json
    output_contract: schemas/nlp_result.json
    prompt_template: null          # llm only
    min_schema_version: 1
    trained_on: null               # optional dataset id from the training repo
    status: planned                # planned | experimental | stable
```

- `planned` entries with empty `hf_repo` are valid, so the registry can be
  populated before models exist.
- Pinning `revision` makes data, prompts and models reproducible together.
- Tests validate the entry and that referenced contracts and prompt templates
  exist. Tests never download models. An optional, opt-in CI job may verify that
  an HF revision exists.
- Required when `status` is `experimental` or `stable`: non-empty `hf_repo` and `revision`.

## 9. Data-integrity tests (`tests/`)

All tests are data-only, run with `pytest`, and gate CI:

- Schema conformance for every YAML file against `schemas/`.
- Uniqueness of entry IDs and registry codes; codes are append-only (compared
  with the previous released registry).
- Referential integrity: every `concept` exists in the registry; every path
  referenced from scoring, context and models resolves.
- Regex safety: RE2-compatible subset and compile check; regex entries declare
  `hit_keywords` or are flagged as always-run.
- Lexicon quality: no duplicate entries after normalization; no entry that is
  also a stopword; `rank` in 1-5 and `ambiguity` in 0-1.
- Normalizer fixtures: each rule file's input → output examples hold, using a
  minimal reference check in the test code only.
- Model registry rules from section 8.
- Language coverage report per concept x language (en, ko, ja, zh-hans, zh-hant); a warning,
  not a failure.

## 10. Evaluation (`eval/`)

- Dataset schema: `text, lang, labels[{concept, span}], source, license`.
- A small gold set for sanity checks, not for training. Large corpora live in
  the training repository.
- Metrics definition: precision/recall per category x language, and the share
  of traffic resolved at each stage. Used to refresh `ambiguity` over time.

## 11. Versioning

- `data_version` (semver) for lexicon/scoring/registry content.
- `schema_version` (integer) for the contracts in `schemas/`.
- A future engine declares the `schema_version` range it supports and resolves
  data from a configured root path (this repository is consumed as a git submodule, not packaged).
- Breaking schema changes bump `schema_version`; term additions bump only
  `data_version`.

## 12. Open items

- Final concept list and rank policy per category (content decision, needs
  policy owner review).
- Exact default numbers for `rank_weight`, `step`, `cap`, router thresholds;
  initial values to be calibrated on the gold set.
- Normalization coverage: the foundation seeds only `strip`, `map`, `strip_between`,
  `nfkc` and `collapse_repeats` rules. Still to add per language: en homoglyph
  tables; ko jamo composition/decomposition and choseong handling (needs
  algorithmic rule types, hence a `schema_version` bump; ko deliberately avoids
  NFKC because it rewrites compatibility jamo); ja hiragana/katakana folding and
  kanji variants; zh-hans/zh-hant homophone and variant-character tables.
- `router.ambiguous_min` (default 0.5) defines an "ambiguous" hit for stage routing.
- Hugging Face organization and repo names (registry entries stay `planned`
  until then).
