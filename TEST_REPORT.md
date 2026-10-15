# Verified follow-up report — October 15, 2026

## Milestone C: latest local verification

Continued clean Milestone B base `4799c328f0c4cfdfd611390afa07042ffbc1ce08`;
all interrupted C changes preserved. **169 passed, 0 failed, 0 skipped**, including
**7 real FalkorDB integration tests and 162 non-integration tests**. One existing
Starlette/httpx TestClient deprecation warning remains. Actual graph tests cover
reconnect/incidence, malformed-upload atomicity, identity/time/contradictions and
timeout preservation of pre-existing records. API/MCP/provider safety tests also
pass. Unit mocks are not counted as actual local inference.

Detailed methodology, domain tables, commands and five readiness answers:
[CONVERTER_AUDIT](CONVERTER_AUDIT.md). Source terms: [DATA_LICENSES](DATA_LICENSES.md).

| Executed measurement | Result and boundary |
|---|---|
| Actual-Falkor dev14 baseline -> final | Binary 2/3/15 -> 4/4/15 (TP/predicted/labelled), F1 22.22% -> 42.11%; AI provisional, mixed public/synthetic |
| Public-only complete subset | 1/1/12 final, recall 8.33%, F1 15.38%; not independent accuracy |
| Entity participant surfaces | 6/6/27 -> 8/8/27, F1 36.36% -> 45.71%; not span NER |
| Whole public event / roles | 0/1 events and 0/4 roles recovered, both baseline/final |
| Final exact quotes | 5/5 emitted records, including unscored cases; provenance only |
| Frozen public23 | All unreviewed; offline 0 claims, metrics empty, 46 records/23 incidence edges consistent; **no F1** |
| Actual Qwen matched4 public dev sources | Baseline 4 calls/0 claims; latest final 5 calls/3 claims/2 reviews; 1/3/9 exact binary, F1 16.67%; offline same texts 1/1/9 F1 20% |
| Actual Qwen frozen4-source probe | 6 calls, 2 accepted/unassessed claims, 6 reviews, 2/2 exact quotes; no semantic score |
| Older inspected synthetic regressions | B12: 6/8 F1 85.71%, 4 events/14 roles; original20: 22/24 F1 95.65%; 26 challenge 17/18/25 F1 79.07% |
| Real100-record CSV / JSON chains | Both passed, 100 claims/101 entities, duplicates/reconnect/repeated IDs consistent; ingest 736.480/744.238ms, write 263.021/303.609ms, two-hop median 6.884/8.372ms |
| Real1,000 and2,000 CSV / JSON chains | All four timed out within upload quotas; empty fresh graphs after failure; no ingestion/query success metric |
| Real public PDF | NASA 1-page biography, 1 claim/2 entities/1 exact quote; rendered layout inspected, no OCR/semantic accuracy claim |
| Three persistent demo domains | Incident/supply authorized action idempotency; research historical/ambiguous identity checks passed; no paid calls |

Final Docker rebuild is healthy (`/ready=true`, backend FalkorDB, provider offline).
Actual packaged HTTP smoke: two contradictory claims uploaded; malformed adjacent
JSON rows returned422 with graph unchanged; `/api/relationships` returned
CONTRADICTED; repeat upload was duplicate; dashboard JavaScript served14634 bytes.
An initial singular-route typo returned404, then the correct plural route passed.
Only the two owned random smoke graphs were removed after checks, not user data.
`/health.live_inference_verified=false` is a static application disclaimer, not
evidence of the host-side Qwen probe; the actual inference reports are separate.

Reports are named `evaluation/c_*.json`; baseline observations are retained.
Independent arithmetic uses `python evaluation/recheck_c_metrics.py`, importing
no scorer helpers. Published model reports contain 15 real calls plus additional
development probes; output variability is disclosed, not best-run cherry-picking.
Exact predicate disagreements are not automatically adjudicated hallucinations.
The final full suite is distinct from the baseline B 130 below. Hosted CI status
must be checked for the pushed SHA; workflow definitions alone are not evidence.

Remaining: independent human annotations, robust broad-prose/event recall,
scalable atomic writes at1,000/2,000, full document/multi-column/OCR support,
production/security/load certification and paid provider validation. None is
represented as done. No unrelated infrastructure or user Docker volume changed.

## Milestone B continuation: final local verification

Recovered the entire interrupted working tree on base `487435f9df92a472a4ad38f29ce970f11a4da1a2`.
No pending source/report/UI changes were discarded or recreated from scratch.
All results below distinguish mocks, provisional labels and real integrations.

| Check | Observed result |
|---|---|
| Unit/API/provider/MCP suite | **126 passed**, 4 integration tests deselected |
| Real FalkorDB suite | **4 passed**, 126 non-integration tests deselected |
| Combined suite | **130 passed**, 0 failed, 0 skipped |
| JavaScript / Python syntax | `node --check` and compile checks passed |
| Targeted new-file Ruff checks | Passed |
| Docker packaging | API rebuilt; API and graph healthy on loopback; no volume removed |
| Real three-domain runner | Incident + supply cases persisted; research time/identity assertions passed; repeat execution idempotent |

One non-fatal Starlette/httpx TestClient deprecation warning remains. Dependency
versions are not fully locked; the successful local environment is not a
guarantee for every future dependency release. Live Bedrock/cloud inference,
production security/load and an externally hosted service are untested.

### Backend corrections and UI

Compact local-model extraction now recovers explicit dates from the matching
grammar relation rather than the first date in an entire multi-sentence quote.
Equivalent grammar/model candidates are deduplicated without collapsing
different external identities or qualifiers. Grammar vetoes wrong event dates
and historical flags. Graph/event endpoint date filters share the same
year/month/day applicability rule; unknown-date claims are excluded from a
historical view. Regression tests cover these cases and a canonical frozen
evaluation-content hash across Windows line endings.

The browser dashboard was exercised against the real Docker API: incident
RULE_DERIVED path, no-write preview, explicitly authorized persistent case
(one saved case became two; open reviews two became four), supply PROVISION
roles/source JSON pointer/exact offsets, dependency path highlighting, zoom/reset,
and research historical filter/name-ambiguity UNKNOWN. Dataset/date changes
reset authorization and stale results. Static asset URLs carry a milestone
version to avoid stale pre-update scripts. Browser console inspection found no
errors. These are manual browser checks, not a committed browser-test suite;
upload/API behavior is covered by automated HTTP tests. Node dragging/panning
and a comprehensive mobile/accessibility matrix are not certified.

### Independently recalculated provisional evaluation

Report: `evaluation/intelligence_final.json`; 12 AI-authored synthetic passages
in seven domains, frozen separately from six development passages. No human
adjudication; similar templates across splits constrain independence. No model
calls in this extraction evaluation. Its storage is memory; actual FalkorDB
workflow correctness is tested separately, not inferred from these scores.

| Metric | TP / predicted / labelled | Result |
|---|---|---|
| Exact binary (direction/predicate/polarity/modality) | 6 / 6 / 8 | P 100%, R 75%, F1 **85.71%** |
| Temporal-strict binary | 6 / 6 / 8 | F1 **85.71%** |
| Whole role-labelled events, including temporal fields | 4 / 4 / 4 | F1 **100%**, very small synthetic sample |
| Participant roles | 14 / 14 / 14 | F1 **100%** |
| Entity surface-set coverage | 25 / 25 / 29 | R 86.21%, F1 **92.59%**; not span NER |
| Exact source quote equality | 10 / 10 emitted records | Provenance only, not independent entailment |
| Empty control abstention | 1 / 1 | Too small for a general safety claim |

A separate calculation using fixture labels and per-case predictions, without
importing evaluator signature/scoring helpers, confirmed temporal binary counts,
whole-event counts, entity counts and macro domain F1 **93.1973%**. This is an
independent arithmetic cross-check, not independent human/model annotation.
Misses: `eval-complex` (appositive employment) and `eval-ambiguous` (complex main
clause). They were not patched to raise evaluation scores. Domain combined F1:
operations 85.71%, research 66.67%; retail/people/geography/supply/finance 100%.
Domains with neither predictions nor labels are omitted from macro scoring. Label disagreement is
0/10; calling that a real-world zero hallucination rate would be misleading.

The prior 26-case challenge was rerun: **17 TP / 19 predictions / 25 labels**,
P 89.47%, R 68%, F1 **77.27%**, five/five empty controls and 19/19 exact quotes.
These are older inspected provisional stress labels, not an unseen test.

### Actual local model observations (not paid/cloud calls)

Stored before/after Qwen development probes each used four documents/four calls,
1,193 input + 197 output tokens. Both yielded three correct binary relations
and one whole event **in the combined rule/model pipeline**, already covered by
rules: no extraction F1 gain. The review-document rate changed **50% -> 25%**:
the dated-employment duplicate no longer becomes a review; flattened BETWEEN
proposals still do. Reports retain original observations/timestamps.

Final-code recheck `intelligence_qwen_verified.json`: four actual local calls,
same token counts and extraction results, 25% review-document rate, zero failed
documents; observed median 2,844 ms / maximum 7,364 ms. Four observations cannot
support p95 or throughput claims. These are development-only probes, not a
held-out model benchmark.

`intelligence_public_qwen.json`: four newly sampled public FewRel sources,
**five actual calls**, 1,555 input + 280 output tokens, **zero accepted claims**,
one document with review tasks. Zero runtime failures does not mean extraction
success. A 24-source queue excludes all previous seed-17 128 sources; all labels
remain unreviewed/incomplete and are excluded from semantic scoring. The four
inspected sources are now development, not unseen. FewRel upstream human
classification annotations do not supply exhaustive sentence-entailment gold.

Across the three development probes and one public probe: **17 actual local
calls**, no paid cloud API charges; local electricity/compute costs unmeasured.
Canonical JSON fixture hashes in current reports differ in format from earlier
raw-file hashes; see `evaluation/ANNOTATION_GUIDE.md`. No hidden data relabelling
or post-hoc score optimization is implied.

### Reproduction and remaining work

```powershell
$env:UGI_TEST_REDIS_URL='redis://127.0.0.1:6380/0'
python -m pytest -o addopts= -q
python -m ugi.eval_intelligence --fixture evaluation/intelligence_eval.json --development evaluation/intelligence_dev.json --output evaluation/intelligence_local.json
python -m ugi.demo --execute --dataset-prefix showcase-b --output evaluation/showcase_local.json
```

Independent human source-entailment adjudication, broader real-world extraction
improvement, recorded demonstration video, organizer/submission review if desired,
paid provider validation and production/public deployment remain unfinished.
No external action or AWS infrastructure was enabled. Hosted CI status must be
confirmed against the exact pushed SHA; the final handoff supplies that run.

## Native n-ary milestone: new measured evidence

The October 15 Codex continuation began at remote main `cf07cf5`, whose
[Actions run 38704495098](https://github.com/divyashy20-boop/graph-hacks-2026/actions/runs/38704495098)
was successful. The first full local continuation suite passed **111 tests,
0 failed, 0 skipped**, including **3 actual FalkorDB integration tests** on the
existing isolated loopback graph service. Later occurrence/identity regressions
are included in the final verification entry below. API/provider model tests
otherwise use mocks or memory, as indicated by test names.

New actual-server test: upload four whole events -> 14 participant-role graph
edges -> exact source evidence -> reconnect -> retrieve events by participant ->
dataset isolation -> idempotent reupload. No entity-pair RELATES/Claim records
were generated from the event spokes. The test deletes only its random test
graphs; the participant's persistent graph volume is preserved.

Unchanged benchmark results (fresh execution, zero model calls):

| Fixture | Exact relation results | Interpretation |
|---|---|---|
| Existing 20-passage development fixture | 22/24 recovered, 22 predictions; F1 95.65% | Tuned synthetic development data |
| Existing 26-case challenge | 17/25 recovered, 19 predictions; P 89.47%, R 68%, F1 77.27% | AI-assisted provisional stress labels |
| Existing UNKNOWN fixture | 12/12 expected status matches | Small synthetic status regression |

Reports: `evaluation/nary_development_report.json`, `evaluation/nary_challenge_report.json`.
These are checks for regression, not a new independent benchmark or a measure of
general event extraction. This workspace also reproduced historical rule F1
15.38% on the 20-passage fixture using the optional adjacent historical package.
That package is not a runtime dependency or included in this repository.

### Actual local Qwen event smoke (development only)

Model: `qwen3:4b-instruct`, host loopback Ollama; 2 documents, 2 actual calls,
no cloud requests. Report: `evaluation/nary_qwen_smoke.json` (public synthetic
text and opt-in raw model trace).

| Document | Model behavior | Final pipeline | Calls / observed latency |
|---|---|---|---|
| Pavo / Quill / Rowan | Two flattened LOCATED_BETWEEN binary candidates, no event | Both binaries held for review; grammar produced one whole BETWEEN event | 1 / 7646 ms |
| Mica / Sensor / Vale Factory | Empty relations list, no event | Grammar produced one PROVISION event | 1 / 497 ms |

Reported token counts: 592 input, 116 output; cloud charge $0. Local compute and
electricity are not free. Latencies are two observations, not a p95 claim. This
demonstrates actual local transport and fail-closed behavior; it **does not show
learned event extraction success**. Event instruction placement was corrected
after this probe; that subsequent prompt change has regression tests but no new
live inference measurement. No paid Bedrock call was made.

### Final local verification for this milestone

**114 passed, 0 failed, 0 skipped** (Python 3.12.14, pytest 9.1.1;
`UGI_TEST_REDIS_URL=redis://127.0.0.1:6380/0 python -m pytest -o addopts='' -q`).
This comprises **111 non-integration tests and 3 actual FalkorDB integration
tests**. One upstream Starlette/httpx deprecation warning remains. Targeted Ruff
and `git diff --check` passed. Docker app rebuild succeeded and a real browser
upload displayed **14 entities, 4 whole events, 0 binary claims** with role
spokes and exact evidence. No persistent Docker volumes were removed.

This report describes the **ChatGPT continuation** of the event implementation supplied as `event.zip`. Prior Codex outputs are clearly distinguished from what was actually reproduced here.

## Code quality and functionality

- Recovered project contained 36 passing functional/API/provider tests and 1 integration test requiring an external FalkorDB service.
- Current project: **47 passed, 1 skipped, 0 failed**, executed in Python 3.13.5 with `pytest` 9.0.2, FastAPI 0.128.2, Pydantic 2.13.5 and local in-memory storage.
- `ugi/mcp_server.py`: typed, bounded MCP JSON-RPC stdio tools added. Handshake, tool listing, read-only evaluation, citation retrieval, write opt-in, actual stdio subprocess all passed locally. Full compatibility with third-party MCP clients not established.
- Python `compileall` completed without syntax errors.
- Real FalkorDB was **not** independently tested in this environment: no Docker engine or Redis driver was available. The missing Redis import was bridged by an **external temporary test-only import shim**, not included in the deliverable. All passing results involving graph writes here used the project's in-memory test backend. This distinction must not be removed from future demo statements.
- No live Bedrock calls, no paid inference, no AWS deployment.

## GitHub Actions independent live integration — October 15, 2026

**Verified successful run:** https://github.com/divyashy20-boop/graph-hacks-2026/actions/runs/38684951348

- GitHub-hosted Ubuntu runner with Python 3.12.15 and installed Redis client.
- **47 non-integration tests passed**, including API/MCP unit and simulated provider checks.
- Docker Compose launched the pinned FalkorDB image and reported the graph container **Healthy**.
- **2 real FalkorDB integration tests passed**, including `test_real_http_persistence_and_isolation`, which exercises actual HTTP upload, two-hop relationship, persisted investigation, review after constructing a fresh API instance, and tenant isolation.
- Synthetic fixture evaluator executed successfully in offline mode.
- No AWS or Bedrock calls were made. The tests establish the listed integration paths on CI infrastructure, **not** production readiness or comprehensive inference accuracy.

## Synthetic evaluation (20 passages; 24 annotated relations; 2 domains)

| Measurement | Initial recovered offline rules | Updated offline rules |
|---|---:|---:|
| Matching target relationships | 16 / 24 | 22 / 24 |
| Predicted relationship count | 18 | 22 |
| Relation precision | 88.9% | 100.0% |
| Relation recall | 66.7% | 91.7% |
| Relation F1 | 76.2% | 95.7% |
| UNKNOWN-status questions | 12 / 12 | 12 / 12 |
| LLM calls | 0 | 0 |

Only a **small synthetic fixture** was evaluated. It is not independently annotated, and changes were guided by seeing the existing fixture's errors; therefore these are **development-set improvements, not an unbiased held-out performance claim**. Do not say universal accuracy improved to 95.7%. Most of the improvement comes from extracting explicit coordinated objects, recognising certain subordinate-clause main claims, and normalising common passive forms. No semantics were inferred from ambiguous pronouns.

`evaluation/current_report.json` contains actual per-sample predictions and qualifier details. B/C/D variants use the same offline extraction candidates; they are **not** separate model comparisons. The historical `A` baseline package was not included in `event.zip`, so it was not run here.

## Implemented follow-up modifications

1. Conservative explicit coordinated-object extraction, e.g. `Mesa depends on Nora and Onyx.` => two candidate relations sharing the original sentence as evidence.
2. Conservative main-clause extraction for `After ..., A VERB B` and `Because ..., A VERB B`; no inference for `If ...` conditions.
3. Normalisation of passive forms like `was deployed by` and `was acquired by`, retaining original predicate strings.
4. `SOURCE_NEGATED` for a standalone negative assertion; `CONTRADICTED` requires an overlapping positive and negative source assertion.
5. `TRANSITIVELY_DEPENDS_ON` now requires a dependency chain of at least two hops.
6. Read-only-by-default MCP stdio tool interface with dual write opt-in and anti-arbitrary-Cypher boundary.
7. Six focused extraction/reasoning regression tests, five MCP tests (including subprocess transport), README, report and safer repository files.
8. Evaluation now additionally records strict subject/predicate/object/polarity/modality relation scores.

## Outstanding blockers (highest first)

1. **Real graph verification:** On a machine with Docker, run `docker compose up -d --build` and `UGI_TEST_REDIS_URL=redis://127.0.0.1:6380/0 python -m pytest -q -m integration`. Check that a restart preserves nodes and actions. Redis package should install from `pyproject.toml` in a network-enabled environment.
2. **Cross-domain generalisation:** Evaluate on genuinely unseen, independently annotated documents and measure precision, recall, evidence correctness and uncertainty separately.
3. **Model-backed semantic extraction:** Obtain explicit authorisation before a small-budget live Bedrock test. Live model quality and model-ID availability are unverified.
4. **Agent reasoning depth:** The deterministic incident policy works, but a general-purpose natural-language agent planner has not been fully built. The MCP tools allow integration with a separate agent.
5. **Deployment hardening:** Strong user authentication, real cost controls, internet HTTPS, monitoring and security review are not yet complete.
6. **Entity disambiguation:** Cross-document identities with the same names require explicit identifiers or manual review and can fragment paths across sources.
7. **MCP compatibility:** Run protocol conformance tests and a real MCP client integration before claiming full interoperability.

The software was not tested in a production-like environment; **a green local unit test suite is not a production-readiness certification**.


## Semantic/identity follow-up — October 15, 2026

Additional coverage:

- `SHARES_EMPLOYER` is RULE_DERIVED only if a two-hop, correctly directed pair of `WORKS_AT` assertions shares one employer and provides temporal anchors with overlap. The returned result includes both supporting claim/evidence records. It is **not** evidence of friendship or direct collaboration.
- Undated employment, nonoverlapping periods and merely co-attending an event do not prove shared employment.
- For provider-assisted extraction, exact same-pair grammar contradictions are still rejected; unrelated parsed clauses no longer suppress independent grounded candidates that require semantic model review. These are mock-provider tests, **not** live Bedrock measurements.
- IDs such as `Person:123` and `Organisation:123` remain separate. Prior untyped IDs in an existing graph can be reused when their stored entity type matches.
- **54 local non-integration tests passed**, 0 failed. See GitHub Actions for live FalkorDB verification on the latest commit. No changes were made to the 20-passage synthetic evaluation fixture; the previously reported F1 score must not be attributed to these new features.



## Participant Windows Docker Desktop smoke test — October 15, 2026

The following results are **reported from the participant's PowerShell/HTTP output**, separate from independently verified GitHub Actions CI. Windows Docker Compose showed both `ugi-event-api-1` and `ugi-event-graph-1` **healthy** with loopback-bound ports `8001` and `6380` respectively.

| Check | Observed result |
|---|---|
| `POST /api/uploads` with `demo/shared_employer.json`, dataset `people` | 2 chunks, 3 entities, 2 claims, 0 reviews; offline provider; no model calls |
| `POST /api/relationships` for `Alice SHARES_EMPLOYER Bob` as of `2021-06-01` | `RULE_DERIVED`, rule `shared_employer_temporal_overlap_v1`, 2 evidence entries |
| Same names/date queried with `FRIENDS_WITH` | `CONNECTED_ONLY`, no friendship asserted |
| `POST /api/uploads` with `demo/incident.json`, dataset `incident-demo` | 8 chunks, 8 entities, 8 claims, 0 extraction reviews |
| `POST /api/investigations` target `Cache`, `authorise_action=true`, idempotency key `first-live-investigation` | `executed=true`, high priority; investigation ID `454db01b874f60081ded5e0c724deda317b3ce0762a9d6ddefe0e44eba51998e` |
| `GET /api/tasks` for `incident-demo` | 2 open review tasks, both linked to the created investigation |

The investigation's **high priority is dependency exposure, not a verified outage**. These outputs demonstrate live graph-backed service operation and immediately retrievable persisted actions. A **subsequent** participant test now demonstrates survival across a coordinated API and FalkorDB container restart, detailed below. Results concern small synthetic demo data, not measured general-purpose AI extraction performance.


## Participant container-restart persistence test — October 15, 2026

**Evidence basis:** PowerShell output supplied in the conversation, not an independently remote-controlled Windows run. On the same installation, the participant ran `docker compose restart`, then `docker compose ps`. After a 5-second pause, the FalkorDB container was **healthy** and the API container was **starting** its health check; API HTTP calls nevertheless succeeded immediately afterward.

Following the restart, the same dataset header `X-Dataset: incident-demo` was used for:

- `GET /api/investigations` => exactly **one** saved investigation, ID `454db01b874f60081ded5e0c724deda317b3ce0762a9d6ddefe0e44eba51998e`, status `open`, target unchanged, priority `high`. The previously created dependency paths, claim identifiers and five-step action trace were still present, including its authorised `create_investigation_and_reviews` step.
- `GET /api/tasks` => exactly **two** original `open` review tasks, IDs `621078a5bc51044c198dd6235f851718a5752c203011d95ded2053c05ddb9946` and `7186f9a68e274f77988829fb0e4ba5888fe4f6e6270ca4a06bd2384aab30b48a`, both referencing the same investigation and the same original claim IDs.

**Result: PASS, restart-and-read durability smoke test.** This provides participant-observed evidence of graph-backed action retention after both app and database containers were restarted. It does **not** test removing the Docker volume, restoring from a backup, abrupt disk failure, concurrent write safety under load or production-grade reliability. Synthetic demonstration data only; no external-world validation of the source claims is implied.


## Extraction generalisation and provider milestone — October 15, 2026

**Independent infrastructure verification:** GitHub Actions run https://github.com/divyashy20-boop/graph-hacks-2026/actions/runs/38694107593 finished successfully, including the full offline unit/API/MCP tests (76 cases), both actual FalkorDB integration tests, the previous synthetic evaluation, the new challenge fixture, and an external FewRel validation download. Local Ollama calls were **mocked only**; no actual model invocation is claimed.

**New 26-sample cross-domain challenge, offline grammar baseline** (`evaluation/challenge_v1.json`):

- 25 manually/AI-assisted annotated directed relations; **17 exact matches**, 19 predictions, precision **89.47%**, recall **68.00%**, F1 **77.27%**.
- Five intentionally empty/no-relation cases; 5 correct abstentions and 0 false alarms on those five.
- 19/19 stored evidence quotes match exact source spans. This is provenance consistency, not a semantic correctness score.
- These novel authored samples are a development stress fixture, **not** an independently annotated external dataset. They must not be pooled with the older tuned 20-case synthetic fixture and labelled an unbiased test.

**External FewRel validation sample, offline grammar baseline** (`ugi/eval_fewrel.py`):

- Source: https://github.com/thunlp/FewRel ; validation file `data/val_wiki.json`; SHA256 `76bb44c2485b6faed358a3ce040eadafcc8a8835245cd7e6afc1bef672d4a0bf`.
- Sample: 128 deterministic (seed=17) examples stratified across 16 Wikidata relation PIDs, drawn from Wikipedia-derived, human-annotated data.
- Head and tail surfaces both present in 120/128 reconstructed source sentences; the extractor emitted any claim in just **1/128** and emitted a correct annotated **directed head/tail pair in 0/128**.
- **Critical limitation:** This measures directed pair discovery only; the evaluator does not compare open predicates against Wikidata PID ontology, hence this is *not* a relation-classification F1 or model quality result. Pair detection alone could still have the wrong predicate.
- Conclusion: Conservative grammar rules are insufficient for ordinary Wikipedia prose. Do not market offline extraction as generally accurate.

**Optional local Ollama implementation**: bounded `/api/chat` calls with schema-constrained results, default provider remains offline, local endpoint validated, no AWS opt-in, failures and invalid JSON persisted for review. Mock-transport tests cover transport/schema/errors, quota, allowed endpoints and integration with offline grammar. **No actual local inference success, latency or accuracy has been measured.** Run a real Ollama sample before public demonstration of that feature.


## Bounded local-model A/B probe and final CI — October 15, 2026

- `ugi.eval_fewrel --local-model MODEL_ID --limit 4 --seed 17 --download` now invokes a **local loopback Ollama endpoint**, contrasting directly with the offline grammar's identically sampled four examples. Up to six examples per run; reports model calls and review tasks, and aborts if the local extraction provider reports failure.
- The Docker-host endpoint is read from validated `UGI_OLLAMA_URL`, with a Windows-host localhost fallback. No remote inference endpoint or Bedrock activation is permitted by this pathway.
- A new mock-transport test covers the CLI's explicit limit and integration path; **the 4–6 actual model samples have not been run**.
- [GitHub Actions run 38694742578](https://github.com/divyashy20-boop/graph-hacks-2026/actions/runs/38694742578) passed: **77 non-integration tests**, **2 live FalkorDB integration tests**, both synthetic evaluation scripts and the 128-example independent FewRel pair diagnostic. All inference was offline/mock-only; do not interpret the green test run as improved relation-extraction quality.


## Participant Qwen3 4B first real local probe — October 15, 2026

**Reported actual Windows + Docker + local Ollama results**:

- Model `qwen3:4b-instruct` listed locally (2.5 GB), Ollama `/api/tags` returned normally, and Docker API reached `host.docker.internal:11434` (HTTP 200). Python project was updated from GitHub and Docker rebuilt.
- FewRel upstream file SHA256 `76bb44c2485b6faed358a3ce040eadafcc8a8835245cd7e6afc1bef672d4a0bf`, first 4 fixed-seed examples: **offline grammar 0/4** target directed pairs, **actual local Qwen 0/4** after 4 model calls, with 0 accepted graph claims and 0 review tasks. User-provided per-sample `predicted` arrays were all empty.
- Source examples involved recall-election dates, bridge/river description, island/geography description, and a boxer/weight class. The benchmark marks head/tail pairs, not explicit sentence entailment; empty output is not always a semantic error. The model returned no accepted candidates. The original provider raw responses were not captured, so emptiness *at the model JSON level* has not yet been directly observed.
- Follow-up engineering: `CompactExtraction` schema for local Ollama, non-SVO relation prompt, deterministic noun-phrase copula guard, and opt-in raw model/semantic review diagnostics. These modifications are tested with mock local transport; **no real model quality improvement has been measured since this code was updated**.
- Regression tests include accepted explicit semantic relation (with a model review), rejection of a false bridge-to-river claim, and a diagnostic distinguishing empty model output from independent grammar candidate creation.

The 4-case comparison is extremely small and not an unbiased precision/recall metric. Do not tune or overfit to the four viewed samples, or force extraction of the FewRel annotated pair when the sentence does not directly support it.


## Participant Qwen3 diagnostic and conservative batch-verification fix — October 15, 2026

### Observed Windows run before batch fix (participant-provided, real local model)

After pulling current `main` and rebuilding the Docker API, the participant ran `qwen3:4b-instruct` on **four** FewRel validation examples (`--seed 17 --limit 4 --diagnose`).

- **8 actual local-model requests**, 2 open review tasks, **4 accepted graph claims** across 2/4 sentences, exact evidence-span check 4/4, **0/4 matching annotated FewRel head→tail pairs**. This is *not* predicate accuracy or relation F1.
- Election-year and boxer sentences returned valid `{"relations":[]}` arrays. Neither alone proves Qwen failed to extract a directly entailed FewRel relation.
- Road/bridge sentence: model proposed `Lane Cove Road ENTERS Ku-ring-gai local government area`; a second independent model prompt approved this interpretation. However, the sentence contains the distinct subordinate subject **A3**, and the participial clause's subject assignment is ambiguous. The model's approval is **not independent evidence**, so this needs human review, not automatic graph assertion.
- Island sentence: model produced `LOCATED_IN` and several `SITUATED_BETWEEN` pairs. `LOCATED_IN Croatian part of the Adriatic Sea` is source-grounded; decomposing a **multi-anchor 'between Lošinj, Unije and Susak'** relation into separate binary `BETWEEN` facts loses semantic qualifiers and should not be silently asserted.
- One response modified exact source quote `Adriatic` into `Adri-atic` and was **correctly rejected**. Another review was skipped when the per-invocation model call ceiling was exhausted.

### Implemented response (GitHub)

- **Single batched semantic-review request** for up to twelve unresolved candidates per local-model passage; deterministic source-span, pronoun, temporal and grammar checks run before the batch. Missing/duplicate indices and candidates beyond the batch budget are held for review, **not accepted**. Structured ingestion and Bedrock review behavior are unchanged.
- Explicit conservative block on flattened binary `SITUATED_BETWEEN` / `LOCATED_BETWEEN` claims; unmodelled n-ary semantics remain human-review tasks rather than false facts.
- Explicit ambiguity guard for agent assignment in participial `entering/crossing` clauses introduced by `where/which/who`; this is a narrow heuristic, **not a general syntax parser**. Ambiguous statements abstain.
- Exact-quote mismatch continues to **reject**, never silently repair or rewrite evidence. Tests assert this rule.
- Added `tests/test_batch_review.py` with batch call-count, valid spatial relation, contradictory relation, quote, group relation, ambiguous subject, incomplete verdict and failed-provider cases. Updated prior Ollama mocked contract tests for the batched schema.
- [GitHub Actions run 38702438378](https://github.com/divyashy20-boop/graph-hacks-2026/actions/runs/38702438378) **passed 86 non-integration tests + 2 actual FalkorDB integration tests**, original synthetic test and 128-case FewRel offline diagnostic. These CI tests use mocked local Ollama responses. The real Qwen **after** this batch fix has **not** yet been run, so no actual before/after model-quality improvement is claimed.

**Limitation:** the current one-object graph edge schema cannot represent genuinely n-ary relations; proper group/event hyperedges remain future work.


## Qwen3 4B real batch review A/B and follow-up — October 15, 2026

**Participant Windows/Docker observations** using the same upstream FewRel `val_wiki.json` SHA256 `76bb44c2485b6faed358a3ce040eadafcc8a8835245cd7e6afc1bef672d4a0bf`, fixed seed=17, sample size=4, local model `qwen3:4b-instruct`:

| Measure | Pre-batch (real Qwen) | After batch (real Qwen) |
|---|---:|---:|
| Actual local model calls | 8 | 5 |
| Sentences with accepted claims | 2 | 1 |
| Accepted graph claims | 4 | 1 |
| Human review tasks | 2 | 5 |
| Correct annotated directed head-tail pairs | 0/4 | 0/4 |
| Exact accepted evidence spans | 4/4 | 1/1 |

The reduction **8 to 5 calls is 37.5%** on these exact four examples, not a representative latency or cost estimate. The only accepted post-batch claim was `Male Srakane LOCATED_IN Croatian part of the Adriatic Sea`. The previously accepted ambiguous `Lane Cove Road ENTERS Ku-ring-gai local government area` was now held for review as an ambiguous participial attachment. Individual flattened `SITUATED_BETWEEN` claims were likewise held, and a verbatim evidence typo (`Adri-atic` versus `Adriatic`) failed exact-span grounding. The subject of the road's trailing participial phrase remains uncertain.

**New false-negative evidence:** The source states that Male Srakane is *just south of Vele Srakane*, yet the small model's batched reviewer rejected `SITUATED_JUST_SOUTH_OF` with a self-contradictory justification. Exact lexical directional entailment should be represented using the weaker base `SOUTH_OF` while retaining the exact source quote, not accepted solely because the LLM asserts it. Following this finding, the predicate normalizer maps directly directional `SITUATED_JUST_SOUTH_OF` and analogous north/east/west variants to their base direction for semantic review. Explicit-source, negation and ambiguity checks still apply.

**Engineering verification:** New direction-normalization regression tests and the original conservative batch tests were run in GitHub Actions; [run 38704185238](https://github.com/divyashy20-boop/graph-hacks-2026/actions/runs/38704185238) completed successfully with all non-integration tests and both real FalkorDB integration tests green. Actual Qwen inference **has not yet been rerun after direction canonicalization**, so any recovery of the one false-negative claim remains unmeasured.

**Interpretation:** FewRel head-tail pair coverage is not the same metric as semantic relation precision, and the sample includes labels not necessarily entailed by the provided sentence. These four inspected examples are now a *development diagnostic*, **not an unseen benchmark**. Further meaningful evaluation requires held-out examples and independently checked relation-level annotations.
