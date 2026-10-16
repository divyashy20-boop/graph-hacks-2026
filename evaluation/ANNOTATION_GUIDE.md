# Evaluation and annotation protocol

## Milestone G freeze and unscored public diagnostic

`g_open_development.json` is AI-authored development/specification data, not human
gold. `g_public_sources_v1.json` freezes32 new FewRel texts and classification notes
selected before the first public probe, excluding prior recorded source texts.
The source-selection hash matches g2_public.json. They are now inspected, not
unseen for future tuning. Original text/PID/hashes/CC BY-SA4.0 attribution stay.
No complete independently reviewed binary/event/qualifier annotations exist.
g2_public_final.json therefore records semantic counts/errors as null/unscored,
not invented F1; directed-pair screening and abstention are separate diagnostics.
Zero emitted spans means quotation accuracy is undefined, not100%.

Human review must create a new derivative/version, preserve source hashes/terms,
annotate complete binary direction/phrase/qualifiers and whole role sets with exact
spans, and supply real reviewers/adjudication. Never change annotation flags or
existing labels to raise scores. `g_novel_public_clause.json` is a convenience
source-selected/manual agent inspection, not independent human-reviewed accuracy;
full-context failure is explicitly retained. See DATA_LICENSES and MILESTONE_G_REPORT.

## Milestone C: source-aware frozen corpus and human derivative

`c_development.json` contains14 AI-provisional development cases (seven public,
seven synthetic). `c_evaluation.json` contains23 unreviewed public cases,
including20 previously uninspected queue records. Their original source freeze
is in `c_manifest.json`; **do not edit or silently regenerate it**. They have now
been run at the final checkpoint and are not unseen for future development.
No independently human-reviewed labels have been supplied. No score is produced
for incomplete/unreviewed cases. The prior B protocol below is historical;
C redistributes selected FewRel excerpts under the explicit [data terms](../DATA_LICENSES.md).

Copy the evaluation file to a local editable derivative. Annotate `binary`,
`events` (entire participant-role set), `entities` and `entity_spans` with exact
`start`/`end` character offsets. Each relationship's `evidence` must be an exact
substring containing its participant surfaces. Preserve qualifiers including
negative/possible/historical, explicit event/interval dates and precision. Do
not invent dates or infer a binary pair from membership in an n-ary event.
Schema defaults are not permission to omit a supported qualifier. Incomplete
ontologies/uncertain scopes must remain `complete=false` and be described in notes.

Only a real reviewer may set `annotation_status=human_reviewed`, populate their
actual nonblank `reviewers` names and declare completeness. Prefer two blind
reviewers plus adjudication; preserve alternatives/notes. Metadata validation
cannot certify reviewer identity or label truth. Original URLs, source hashes,
licences, locator and text must remain unchanged. The promotion tool requires
review declarations and a new output directory, never overwriting the source.

```powershell
Copy-Item evaluation/c_evaluation.json .evaluation-local/c_human_edits.json
# Humans edit the copy; do NOT automatically relabel all cases human_reviewed.
python -m ugi.review_conversion_annotations --edited .evaluation-local/c_human_edits.json --output-dir evaluation/c_reviewed_v1
python -m ugi.conversion_audit --fixture evaluation/c_reviewed_v1/c_evaluation.json --development evaluation/c_development.json --final-checkpoint --output evaluation/c_reviewed_v1/offline.json
```

The tool rejects a copy without review declarations. Canonical hashes and source
leakage checks protect provenance, not semantic independence: near duplicates
are checked lexically; FewRel's original Wikipedia-article identity is unknown.
Full source-aware graph audit commands and limits are in
[CONVERTER_AUDIT](../CONVERTER_AUDIT.md).

## Historical B annotation protocol

There are three distinct evidence sources. Do not pool their numbers.

1. `intelligence_dev.json`: six authored development passages; provisional
   AI-assisted labels. Suitable for diagnosing failures and regression tests.
2. `intelligence_eval.json`: twelve authored evaluation passages, frozen before
   this milestone's extraction changes. Provisional AI-assisted labels, seven
   domains. Original LF-file SHA256 `08e7744dc646d1c83fe25d50116f658c91568b0d1b1d129a804568be368514de`.
   Its results were examined after the targeted development fixes; do not tune
   on its errors and continue calling it unseen.
3. Public FewRel queue: genuinely new source sentences, excluding all 128
   previously inspected seed-17 diagnostic sources. The upstream human PID
   annotations describe relation classification; they do not exhaust all
   source-supported relationships or prove sentence-level entailment.

Current reports use a platform-independent **canonical JSON** SHA256 (sorted
keys, compact separators, UTF-8), not raw Windows/LF file bytes. The evaluation
content hash is `b534b5d70492d113f0400d308bfe00458c28cf7b0ba5bda5f2453075e33e8b73`,
locked by a regression test. Earlier before/after Qwen reports retain their
original raw-file hashes and timestamps; do not silently rewrite observations
or interpret this hashing-format change as changed annotations.

## Reproduce public annotation queue

```powershell
py -m ugi.prepare_annotations --download --count 24 --output .evaluation-local/fewrel_queue.json
```

Upstream data: [THUNLP FewRel](https://github.com/thunlp/FewRel), Han et al.,
EMNLP 2018. Original Wikipedia-derived validation data distributed under
[CC BY-SA 4.0](https://thunlp.github.io/1/fewrel1.html). Original file SHA256:
`76bb44c2485b6faed358a3ce040eadafcc8a8835245cd7e6afc1bef672d4a0bf`.
Sampler seed 20261015; it excludes original seed-17 128 sources and duplicate
sentence hashes. Download and queue are kept local, not silently redistributed
under the code's licence. Retain upstream attribution and share-alike terms if
sharing the annotated derivative. Public source text only; no private data.

The initial queue hash is
`3bfb3b39de997ffa93fbac7ac2602cdf78139665bf79ab02e0f5f2141c9ca9a4`.
All 24 records initially have `annotation_status=unreviewed` and `complete=false`.
The evaluator excludes them from precision/recall and unsupported-rate scoring.
Their extraction outputs and review decisions can still be inspected. Four
fresh sources have already been used for a model diagnostic and must now be
treated as development examples. Reserve remaining sources before annotation.

## Human reviewable file

For each source, annotate all named directed relations in `binary`, whole
role-labelled groups in `events`, and relation participants in `entities`.
Preserve negation, modality, historical scope and explicit dates. Review exact
text: do not use an upstream Wikidata label as proof of information absent from
the sentence. Mark uncertain scope in `notes`; an incomplete case must keep
`complete=false`. Never count unannotated predictions automatically as wrong.

Set `annotation_status=human_reviewed` only after a real person checks it and
adds their name in `reviewers`. Ideally two reviewers independently annotate,
then adjudicate disagreements; the code cannot certify the truth of reviewer
metadata. Keep original labels, review changes and adjudication notes in Git.
Promote the reviewed fixture to a separate evaluation split; verify no overlap
with development source text/IDs. Add its hash before changing algorithms.

```powershell
py -m ugi.eval_intelligence --fixture .evaluation-local/fewrel_queue.json --output .evaluation-local/offline.json
# Explicitly bounded actual local inference, at most six sources:
py -m ugi.eval_intelligence --fixture .evaluation-local/fewrel_queue.json --local-model qwen3:4b-instruct --limit 4 --output .evaluation-local/local-model.json
```

## Metrics and boundaries

Binary signature = subject, canonical predicate, object, polarity, modality.
Temporal signature additionally requires event time, interval and historical
flag. Event signature additionally requires the complete role/participant set.
Role-only scores complement, but do not replace, exact whole-event correctness.
Entity scores are surface-set participant coverage, **not span NER F1**.
Identity correctness and multi-hop/action correctness are exercised by the
three-domain workflow assertions and real graph integration tests, separately
from text extraction scores. No unsupported truth probability is reported.

Only complete provisional/human-reviewed cases receive precision/recall/F1.
Provisional scores remain provisional. Label-disagreement rates are not a
human-adjudicated hallucination rate. Quote equality is provenance correctness,
not semantic correctness. Empty controls test abstention. Reports include domain
F1, model calls/tokens, review-document rate, failures and latency observations.
Local inference cloud charge is zero; compute/electricity cost is unmeasured.

SciFact was considered as a second public domain: its claims/evidence are
[CC BY 4.0 and abstracts ODC-By 1.0](https://github.com/allenai/scifact/blob/master/LICENSE.md).
Its support/refute task is different from relation extraction. No SciFact relation
F1 is claimed or fabricated; a task-specific adapter and review remain future work.
