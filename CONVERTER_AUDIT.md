# Conversion quality gate

## Milestone G open predicate boundary

Optional open_predicates adds bounded literal phrase/group frames and a provisional
semantic registry, not unrestricted NLP. Structured unknown predicates and novel
prose are tested separately. Authored dev12 recovers8/8 binaries and2/2 whole events;
frozen public32 emits0 in both modes and lacks complete source-entailment labels,
so semantic metrics are unscored. A new exact public clause works, its full longer
sentence abstains. Schema state is not truth and cannot grant inference. See
MILESTONE_G_REPORT for real graph evidence, source terms and limitations.

## Milestone E scope boundary

The new opt-in identity ledger is a **storage/history and provisional projection**
foundation, not a language extraction improvement.209 tests pass including13
real graph tests. Typed source-ID rename/card history, distinct same-name people,
immutable mentions, reversible authorized demo decisions and targeted artifact
staleness are tested. Current Claim/Event identity anchors are not rewritten;
provisional projections cannot be used as definitive evidence. Legacy records
are not retrospectively reconstructed from mutable Entity profiles.
Actual ledger-off development graph results remain10/10/15, public7/7/12.
Three demos and all six ledger-off chain sizes pass again. Ledger-on100-row exact
payload/incidence check passes; its200-mention cap is not general capacity.
Independent merge/split accuracy, autonomous wrong-merge detection and semantic
re-evaluation are not evaluated/implemented. Research/design choices and deferred
domain-pack/open-predicate work are explicit in docs/UNIVERSAL_ARCHITECTURE.md.

## Milestone D graph update — October 16, 2026

191 automated tests pass including10 real graph integrations. Fresh100/1,000/2,000
CSV and JSON chains all pass with exact persisted payloads and incidence under
the unchanged5,000ms query budget. Independent repeat/isolation/query checks and
three-domain controlled restart hashes pass. Existing/shared identity updates
still use the prior writer: large mixed-upsert scaling remains a limitation.
This changes measured fresh-write capacity, not language accuracy. The complete
provisional audit still yields10/10/15 (F1 80%); public7/7/12 (F1 73.68%). Research
event recall and independent annotation gaps remain. See MILESTONE_D_REPORT and
the preserved baseline/intermediate/final performance reports; no general
production, million-record, arbitrary-prose or whole-document claim follows.

## Milestone D extraction update — October 16, 2026

The controlled first increment improves the same provisional public complete
development subset from1/1/12 to7/7/12 (TP/predictions/targets), F1 15.38% ->
73.68%, recall8.33% ->58.33%. Mixed binary/qualified F1 42.11% ->80% (10/10/15).
No new human annotation or unseen evaluation is claimed. Five public binaries
and the research event still have no proposal. Actual Qwen final7/8/9 versus
rules-only7/7/9 shows no extra exact recall; the remaining additional source-backed
occupation uses a different predicate than provisional labels, requiring review.
186 tests pass including7 actual graph tests. No graph-store optimization is part
of this increment. Full diagnosis, rejected/accepted cases, limits and commands
are in [MILESTONE_D_REPORT](MILESTONE_D_REPORT.md). Historical C measurements below
are preserved rather than overwritten.

## Milestone C audit (historical)

Measured locally on October 15, 2026, continuing Milestone B
`4799c328f0c4cfdfd611390afa07042ffbc1ce08`. This is a useful, conservative
graph prototype, **not a universally accurate converter or production system**.
Passing graph/API tests does not compensate for low public-prose recall.

## Method and provenance

The audit executes TXT ingestion, extraction, identity resolution, claim/event
creation, actual FalkorDB writes and retrieval through a newly connected store.
The final runner compares every stored record payload and reconstructs all
HAS_CHUNK, SUPPORTS, CITES, RELATES and role-labelled HAS_PARTICIPANT incidence.
It never projects event anchors into binary facts. Random audit/performance
namespaces are deleted after verification; existing demo graphs and Docker
volumes are retained. Baseline reports predate the additional incidence check.

`c_development.json` has 14 cases: seven curated public excerpts across
operations, supply, research, organization, history, finance and spatial prose,
plus seven synthetic safety cases. Texts include appositives, lists, nested
clauses and multi-party events, not just simple SVO templates. These are short
excerpts, **not full-document understanding benchmarks**. All labels are
AI-authored provisional, including scope/completeness declarations. Five public
cases are scored; finance/spatial partial annotations are excluded. Incomplete
safety cases are excluded too, never treated as empty gold.

`c_evaluation.json` freezes 23 **unreviewed** sources: three reserved NASA/NIST
excerpts and the remaining 20 records from the prior 24-source FewRel queue.
The four sources already inspected in B were excluded. Development and evaluation
IDs, text and exact URLs are disjoint; four-word shingle containment >=0.65 is
rejected. This is lexical separation, not proof of semantic independence or
absence from model pretraining. FewRel URLs identify dataset records, not original
Wikipedia articles, so article-level separation cannot be certified.

Canonical JSON hashes are frozen in `c_manifest.json`: development
`44862ce81022f36925e6191146b5a44eafef2f9aedd83dadb26f752437f14861`,
evaluation `b154cf6ec455e9e3658833f36c8bcc5e39d12e773a8763dc3decb5501b0f07fe`.
Sources, titles, licences, locators and exact UTF-8 excerpt hashes accompany
the fixtures; these are not hashes of entire downloaded web pages. See
[data attribution](DATA_LICENSES.md) and [human protocol](evaluation/ANNOTATION_GUIDE.md).
Frozen outputs were first examined only at the final checkpoint, after fixes;
they must not now be called unseen for future tuning.

## Before/after: provisional development, not unbiased accuracy

Exact binary matching requires directed subject/predicate/object, polarity and
modality. Qualified matching additionally requires dates, precision and historical
scope. Whole-event matching requires the entire role set. Entity figures measure
relation-participant surface sets, **not exhaustive entity-span NER**. Missing
supported targets count as false negatives. Directed pairs are reported separately
and never substituted for relation F1.

| Offline development measure | Before | Final |
|---|---:|---:|
| Binary TP / predicted / labelled | 2 / 3 / 15 | 4 / 4 / 15 |
| Precision / recall | 66.67% / 13.33% | 100% / 26.67% |
| Binary and qualified-binary F1 | 22.22% | 42.11% |
| Participant-surface TP / predicted / labelled | 6 / 6 / 27 | 8 / 8 / 27 |
| Participant-surface F1 | 36.36% | 45.71% |
| Whole public research event / roles recovered | 0 / 1; 0 / 4 | 0 / 1; 0 / 4 |
| Exact quotes, including unscored outputs | 4 / 4 | 5 / 5 |

**Public-only complete subset:** before 0 predictions / 12 binary targets;
final **1 TP / 1 prediction / 12 targets**, recall **8.33%**, F1 **15.38%**.
The other three final matches are synthetic controls. Mixed 42.11% is not public
accuracy. Quote equality proves text provenance, not source entailment or truth.
`evaluation/recheck_c_metrics.py` independently recomputes recorded binary counts
without importing UGI scorer helpers; this validates arithmetic, not annotations.

Final domain counts below combine binary and whole-event targets as explicitly
labelled in the report; do not confuse this with binary-only micro F1.

| Complete domain | TP / predicted / targets | Interpretation |
|---|---:|---|
| Public operations | 1 / 1 / 2 | Main LED clause recovered; former affiliation missed |
| Public supply | 0 / 0 / 5 | Contractor/responsibility list missed offline |
| Public research | 0 / 0 / 1 event | Whole intersection event missed |
| Public organization | 0 / 0 / 2 | Complex career prose missed |
| Public history | 0 / 0 / 3 | Nested removal/installation relations missed |
| Synthetic safety | 3 / 3 / 3 | Narrow controls, not a real-world domain ranking |
| Finance / spatial | Not scored | Partial annotations; zero offline outputs |

Reports: `c_baseline.json`, `c_development_final.json`. The final complete-set
failure count is 11 missing binary relations and one missing event. No remaining
complete-set offline label disagreements does **not** establish zero hallucination.
Candidate-free chunks can contain many real relationships; ingestion now returns
an explicit coverage warning rather than equating silence with semantic success.

## Ranked failures and focused changes

1. **Candidate recall (highest frequency):** 13 missing baseline binaries and a
   missing research event. Broad prose parsing is high effort. Added bounded
   noun-phrase appositive recovery, numeric name components and lowercase
   mission/investigation/project suffixes; retained complete quotes. This recovers
   the main operations clause, not all relations. Relative/conditional clauses
   remain conservative. No document-specific entity/predicate lookup was added.
2. **Qualifier/entailment loss (high severity):** modal `might not` now preserves
   negative/possible; strict date-tail parsing no longer discards conditional,
   contrasting or attribution tails. Source-present attribution, exact temporal
   precision and whole-word entity grounding are required even if a model approves.
   Earlier unsafe-tail acceptance now abstains, but automatic comprehensive
   review-task generation for every missed clause is not implemented.
3. **Structured corruption risk (high severity, bounded effort):** preflight all
   CSV/JSON rows before extraction/writes; partial triples, missing cells,
   whitespace-only names, duplicate JSON keys, non-finite numbers and malformed
   PDFs fail safely. Valid neighbouring rows are not partially committed.
4. **Predicate consistency:** OWN/USE normalize to OWNS/USES; read-time comparison
   handles legacy stored spellings without migrating user data. Evaluators apply
   the same fixed aliases to both labels and predictions; labels/thresholds were
   not changed to hide a regression. Earlier broad-copula safety guards remain.

Positive, negative and preserved-function regressions cover these changes.
Controlled tests cover identical names, type-separated external IDs, repeated
sources, contradictory documents, time scopes, unclear pronouns, injected source
instructions, malformed structured uploads and real reconnect/tenant separation.
They are not independent public identity-resolution precision/recall estimates.

## Actual local AI, not mocked inference

Ollama `qwen3:4b-instruct` was reached on the Windows host. Identical first four
public development texts were compared, with per-document call limits and no
cloud requests. Baseline: **4 calls, 0 accepted claims**, nine binary targets and
one event. Final observed rerun: **5 calls, 3 accepted claims, 2 review tasks**,
one exact binary match / nine targets, precision33.33%, recall11.11%,
F1 **16.67%**, no event. Final per-document wall times: 421.765, 8362.358,
364.738 and 257.994ms (extraction, review and persistence, not pure inference).

Offline on those same four texts accepted one rule-covered correct binary and
no other claims: **1 / 1 / 9**, F1 **20%**. Qwen therefore did not improve exact
relation recall and reduced exact precision in this observation. Two accepted
RESPONSIBLE_FOR edges omit the building qualifier used by provisional labels;
they are predicate/qualifier disagreements, **not proven invented facts**.
One source-supported preparing-for-launch candidate was rejected by the local
semantic reviewer; one candidate failed entity-surface grounding. The model
reviewer is fallible, not an independent judge. Earlier reruns emitted only the
rule-covered claim, showing output variability even on the same source material.
We retain the latest observation, not the best-scoring probe. No evaluation-label
tuning followed the frozen checkpoint. Raw model trace for every intermediate
probe was not retained; do not infer the exact raw response from accepted counts.

Frozen final checkpoint: offline **23 sources, 0 accepted claims/events**, while
sources/chunks persisted and reconnected consistently (46 records, 23 incidence
edges). Four-source local probe: **6 calls, 2 accepted claims, 6 reviews**, 2/2
exact quotes. **All 23 labels remain unreviewed: no semantic F1, unsupported rate
or correct-abstention claim is possible.** The two accepted frozen predictions
are unassessed, not declared correct/false. Published baseline/final/frozen model
reports account for 15 real calls; additional bounded development probes also
ran. Cloud API charge $0; local compute/electricity unmeasured. CI uses no model.

## Capacity and persistence gate: partial failure

`c_performance_final.json`: actual FalkorDB, default quotas (2,000 records,
200,000 characters, 5MB upload), explicit dependency chains, no local model.
Single traced measurement per size/format, not p95/throughput or controlled
before/after speedup. Existing server budget remains TIMEOUT_MAX=5000ms.

| Input | Result | Ingest / write ms | Two-hop median ms | Python allocation peak |
|---|---|---:|---:|---:|
| 100 CSV | Passed: 100 claims, 101 entities | 736.480 / 263.021 | 6.884 | 3,092,155 bytes |
| 100 JSON | Passed: 100 claims, 101 entities | 744.238 / 303.609 | 8.372 | 2,856,188 bytes |
| 1,000 CSV / JSON | Query timeout | Failed; write6048.918 / 5949.571 | Not measured | 28,219,117 / 28,328,698 bytes |
| 2,000 CSV / JSON | Query timeout | Failed; write6893.262 / 6917.077 | Not measured | 56,600,681 / 57,056,306 bytes |

Failed graphs had zero records after failure. A separate real integration test
also preserves a pre-existing dataset payload snapshot after a timed-out upload;
on a faster server full success is allowed only if every expected record remains.
Successful100-record duplicate uploads added no records (4.083/3.808ms), fresh
connections had equal counts, and independent dataset repeats had identical
claim IDs without cross-dataset records. The CPU field is Python-client process
time (218.75/281.25ms for successful CSV/JSON), not server/host CPU utilization;
memory is tracemalloc allocation peak, not RSS/GPU/container memory. Five query
samples cannot establish production latency. Failed runs have no ingestion or
query success metric. A successful benchmark command means observations were
recorded; inspect each `success` field.

An attempted single-query bulk-write optimization failed isolated integration
checks and was **rejected**. The known-good transactional writer is retained;
no timeout increase, partial-document batching or user-volume deletion masked
the capacity defect. HTTP503 now advises reducing size and inspecting before
retry. **The 2,000-record validation ceiling is not a proven ingestion capacity.**

## PDF, regression and demonstration checks

An actual downloaded one-page NASA Armstrong biography PDF was ingested through
pypdf into real FalkorDB: one claim, two entities, one exact quote; no model.
`c_pdf.json` records download SHA, page count and timings. The PDF page was
rendered and visually checked: photograph, wrapped paragraphs and sections.
This is limited layout coverage, not a multi-column/OCR benchmark. A separate
14.3MB newsletter exceeded the5MB limit and was not ingested. Scanned-image OCR
remains unsupported. No PDF semantic accuracy score is asserted.

Older inspected regressions remain separate: B synthetic12 retains6/8 binary
targets, F1 **85.71%**,4/4 events,14/14 roles; original synthetic20 retains22/24,
F1 **95.65%**; prior26-case challenge improves17/19/25 to17/18/25, F1
**77.27% ->79.07%**, removing one unqualified attributed acceptance. These tiny
AI-authored/template sets do not override weak complex-public results. Reports
`c_legacy_regression.json`, `c_original_regression.json`, `c_challenge_regression.json`.

Actual persistent incident/supply/research demonstrations passed again in
`c_showcase_live.json`: authorized action idempotency, explicit dependency paths,
unprojected PROVISION roles, historical employer overlap and ambiguous-name
UNKNOWN. They demonstrate graph semantics on structured synthetic evidence,
not comprehensive natural-language conversion. No UI redesign was attempted.

## Capability matrix and five readiness answers

| Category | Supported claim |
|---|---|
| Verified working | Small explicit CSV/JSON triples/events; exact source spans; actual persistent graph incidence/reconnect; bounded explicit rules; isolated authorized actions; controlled identity/contradiction safety |
| Working but limited | Simple prose grammar, qualified dates/negation, small text PDFs, dashboard;100-record local chain, not all quota-sized uploads |
| Experimental | Qwen candidate generation/review; complex prose and event extraction; open-ended predicate normalization; model reviews can reject supported statements |
| Unsupported | Scanned PDF OCR; universal coreference; automatic fact/truth certification; public production-scale hosting or capacity guarantee |
| Requires human review | Frozen23 public sources, completeness/ontology of provisional labels, unassessed claims, independent entity/relation accuracy and adjudicated domain ranking |

**How reliably does UGI create the right graph?** Structurally consistent on
executed real-graph checks, but semantic completeness is poor on complex public
prose. Public complete-set recall8.33% is provisional, not a general estimate.

**Where does it miss relationships?** Appositive affiliations, contractor lists,
nested career/history clauses, abstract multi-party events, indirect phrasing and
unresolved pronouns; conservative or fallible model verification also loses recall.

**Where does it invent or overstate relationships?** Baseline modal/qualifier loss
and ignored tails were concrete safety failures now regression-covered. Local
review still accepts underspecified predicates and rejects some supported ones.
An exact quote alone is no guarantee; independently adjudicated hallucination
rates cannot yet be calculated. Claims remain source assertions, not verified truth.

**Which domains work best?** Explicit operational dependency/structured supply
and research demo records work. The new complete public operations subset recovers
one clause; other public domains have zero offline recovery or incomplete labels.
This sample cannot justify a reliable general domain ranking.

**What can we demonstrate confidently?** Three synthetic evidence-to-action
flows, persistent source/role inspection, temporal UNKNOWN versus sound rules,
safe ambiguity, small structured uploads and honest coverage/review warnings.
Do not present B85.71% as real-world accuracy or promise2,000-record conversion.

## Reproduce on Windows

From the existing repository root, with its Python environment activated:

```powershell
python -m pip install -e '.[test]'
docker compose up --build -d --wait
$env:UGI_TEST_REDIS_URL='redis://127.0.0.1:6380/0'
$env:UGI_ALLOW_PAID_CALLS='false'
python -m pytest -o addopts= -q
python -m ugi.conversion_audit --fixture evaluation/c_development.json --output evaluation/c_development_local.json
python -m ugi.conversion_audit --fixture evaluation/c_evaluation.json --development evaluation/c_development.json --final-checkpoint --output evaluation/c_evaluation_local.json
python evaluation/recheck_c_metrics.py
python -m ugi.benchmark_conversion --output evaluation/c_performance_local.json
python -m ugi.demo --execute --dataset-prefix showcase-b --output evaluation/c_showcase_local.json
# Optional ACTUAL local inference; never AWS/paid cloud:
$env:UGI_OLLAMA_URL='http://127.0.0.1:11434'
python -m ugi.conversion_audit --fixture evaluation/c_development.json --local-model qwen3:4b-instruct --limit 4 --output evaluation/c_qwen_local.json
# Optional public PDF download; quota checked, no cloud inference:
python -m ugi.audit_pdf --download --output evaluation/c_pdf_local.json
```

The active development machine already ran these checks; the user does not need
to repeat them for this handoff. Independent human annotation and a safe scalable
writer remain follow-up work. No Bedrock, unrelated Khoj infrastructure, paid
hosting or Docker volume deletion was enabled.
