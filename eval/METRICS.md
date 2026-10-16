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
