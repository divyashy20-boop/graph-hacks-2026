# Event-time implementation work log

## Native multi-participant relations — October 15, 2026 (Codex continuation)

- Continued from verified remote main `cf07cf5`; its Actions run 38704495098
  succeeded. The Downloads working tree was clean but behind remote main. Used
  a clean clone in the authorized workspace; no nested event directory.
- Added typed RelationEvent/participant schemas, exact evidence, role-labelled
  graph incidence edges, atomic ingestion, type-scoped identities and review.
  Binary claims and their reasoning paths remain compatible. Supported event
  grammar: clear BETWEEN, provision, acquisition and research collaboration.
- Added event retrieval/filter endpoints and source-connected event diamonds.
  Added mixed binary/event and four-event synthetic demos. No general binary
  inference is licensed by participant co-membership.
- Corrected an optional historical evaluator adapter failure found locally:
  RuleExtractor expects a list of chunks. It now executes where the old package
  is available and still reports unavailable in a standalone checkout.
- First full run: 111 passed, including 3 actual FalkorDB integration tests;
  added further repeated-occurrence/identity regressions afterward, final count
  recorded in TEST_REPORT.md. Existing development and challenge scores unchanged.
- Local Qwen smoke: 2 actual local calls, one per synthetic document. Qwen gave
  two flattened BETWEEN candidates (withheld) and empty supply extraction. Both
  whole events came from grammar. No learned n-ary extraction improvement.
  Subsequently moved event instructions before SOURCE; post-fix model behavior
  remains unmeasured. Exact raw responses are in evaluation/nary_qwen_smoke.json.
- New independently human-annotated evaluation, general natural-language agent
  planning and full UI redesign remain subsequent milestones; no claims otherwise.
- No paid Bedrock, cloud deployment, public endpoint, volume deletion, force push
  or changes to Khoj. AI-assisted development disclosed; participant review remains
  necessary. Publishing and CI result are recorded after verification below.
- Final local suite: **114 passed, 0 failed, 0 skipped**, including 3 live
  FalkorDB integration cases. Targeted lint/whitespace passed. Docker rebuild
  succeeded; browser upload showed 4 events/14 entities/0 flattened binary claims.

## Historical Codex stage — October 15, 2026

Started 2026-10-15 09:26 IST (03:56 UTC), within the event window, according to the supplied historical `WORK_LOG.md`.

Historical `UniversalGraphConverter.zip` was kept as a baseline, with event work inside `event/` rather than overwriting `src/universal_graph`. The historical baseline was not included in this `event.zip` upload.

- [x] M0: inspect prototype; Codex reported collecting 148 historical tests.
- [x] M1: first end-to-end event package, extraction, FalkorDB store, incident investigation and persisted action code.
- [x] M2 (part): evidence validation, bounded model parsing and temporal/status semantics.
- [x] M3 (part): interface and two domain-specific demo fixtures.
- [ ] M4 (part): real server integration reportedly fixed by Codex; not reproduced in the continuation environment.
- [ ] M5: public deployment/video/repo submission still needs human approval and actions.

Docker engine was initially stopped in the original Codex workspace; Codex reported testing reconnect after fixing index creation. No paid cloud deployments were authorised.

## ChatGPT continuation — October 15, 2026

- [x] Read supplied `event.zip`, safely extracted to a separate workspace.
- [x] Reproduced original suite locally, using an external Redis import shim **only** because the `redis` library and FalkorDB server are unavailable here. Original 36 test functions passed; one live-integration test skipped.
- [x] Added conservative coordination, main-clause and passive predicate improvements; guarded against arbitrary trailing clauses.
- [x] Corrected source negation versus actual conflicting source claims; corrected transitive dependency minimum path length.
- [x] Added bounded application-specific MCP stdio interface and read/write permission separation.
- [x] Added tests for new extraction, semantic safeguards, MCP handshake, persistent local action, and actual stdio subprocess.
- [x] Reran updated tests: **47 passed, 1 skipped**. Ran Python syntax compilation.
- [x] Ran the local synthetic offline benchmark: initial 16/24 targets, updated 22/24 targets. This is **not** an unbiased production-quality accuracy claim.
- [x] Added README, evaluation outputs, report, `.gitignore` and `.dockerignore`.
- [ ] Retest all integrations against real FalkorDB and authorized Bedrock outside this environment.
- [ ] Deploy behind HTTPS and authentication after user's explicit permission.
- [ ] Record demo and submit the repository as required by organisers.

Key implementation constraints: FalkorDB remains required for production/demo persistent graph mode; in-memory backend is for tests only. No GNN training was attempted, and no AWS resources were changed.

## GitHub integration verification update — October 15, 2026

- [x] Verified public repository main contains the event source, sample data and docs.
- [x] Added `tests/test_http_integration.py`: real HTTP upload → FalkorDB evidence/reasoning → saved investigation → fresh API instance → review workflow → isolation, with temporary test-only graphs.
- [x] Added `.github/workflows/verify.yml` to run unit/MCP/API tests and real FalkorDB integration tests on push or manual dispatch. Provider is offline; no AWS usage is triggered.
- [x] Re-ran local non-integration checks: 47 passed; the two real-server integration checks are skipped locally because this environment lacks Docker/Redis. GitHub Actions run result is not yet verified.
- [x] Updated README with CI behavior and Windows checkout sync instructions.
- [x] Verified GitHub Actions run 38684951348: 47 non-integration tests plus 2 real FalkorDB integration tests passed on hosted Docker, benchmark command completed. See TEST_REPORT.md.
- [x] Participant Windows Docker Desktop walkthrough: uploaded employer and incident graph, observed RULE_DERIVED versus CONNECTED_ONLY, executed authorised investigation, and retrieved two persisted review tasks. Subsequent API+FalkorDB container restart retained the exact investigation ID, action trace, paths, and both review-task IDs. See TEST_REPORT.md; this is a restart/read smoke test, not backup/disaster recovery.


## Evidence-aware relation milestone — October 15, 2026

- [x] Added a typed two-hop `SHARES_EMPLOYER` derivation that requires evidence-backed `WORKS_AT` edges through the same employer, both temporally anchored, and overlapping validity. Other shared-node paths and undated relations remain CONNECTED_ONLY or UNKNOWN, not relationships invented by proximity.
- [x] Fixed overbroad grammar rejection: an unrelated parsed clause no longer vetoes a separate grounded LLM extraction candidate; mismatched same-pair predicate/direction/polarity remains rejected.
- [x] Namespaced explicit entity identifiers by declared type to prevent cross-type false merges, with safe reuse of existing legacy IDs when their stored type matches.
- [x] Added regression examples and a `demo/shared_employer.json` walkthrough.
- [x] Local non-integration suite: 54 passing tests, 0 failures. Actual real-FalkorDB CI outcome for this final commit is checked separately.
- [ ] Independently benchmark these changes on novel documents and live Bedrock before making broader accuracy claims.

## Restart persistence verification — October 15, 2026

- [x] Both containers restarted with `docker compose restart` on the participant's Windows host. FalkorDB reported healthy, and API requests immediately after startup succeeded.
- [x] Read back the **same** investigation `454db01b874f60081ded5e0c724deda317b3ce0762a9d6ddefe0e44eba51998e` plus both original review tasks. Review/action trace and source claim IDs persisted.
- [x] Logged the exact test and its limitations to `TEST_REPORT.md`, and updated the `README.md` submission checklist.
- [ ] Complete an independently annotated unseen-document evaluation and verify model-backed semantic extraction separately, before broader accuracy claims.
- [ ] Record hackathon demo video and submit form after final review.


## Challenge evaluation, external baseline and local-model adapter — October 15, 2026

- [x] Created and froze `evaluation/challenge_v1.json` (26 AI-assisted synthetic stress cases) separately from the prior tuned synthetic fixture. Added `ugi/eval_challenge.py` for strict relation/qualifier scores, negative control abstention, exact evidence-span checks and per-domain diagnostics.
- [x] Created `ugi/eval_fewrel.py` with explicit download of upstream FewRel Wikipedia-derived human-annotated validation data. Fixed sample of 128 cases, zero model calls, head/tail directed-pair screening only. GitHub Actions archived per-sample output; baseline emitted 1 claim and correctly extracted 0/128 target pairs, revealing a major generalisation gap.
- [x] Added `Engine.resolution_gap`: paths now come with typed predicate/direction sequences, missing evidence and recommended verification actions; missing/ambiguous entity identity returns its own diagnostic. No new inferred fact is promoted from proximity.
- [x] Added opt-in local `Ollama` backend (restricted URL, Pydantic JSON schema, bounded retries/calls, persisted usage and invalid-result reviews); wired Settings, Engine, Compose and .env.example. Default offline and paid calls disabled.
- [x] GitHub CI verified syntax, unit/adapter tests, live FalkorDB integration, synthetic and upstream validation diagnostics. `README.md` documents the poor external grammar baseline and local Ollama setup.
- [ ] Run a real model locally on Windows with explicit user setup. **No claim of improved extraction precision/recall/F1 yet.**
- [ ] Develop a separate truly independent evaluation split to avoid overfitting after reviewing FewRel results.


## Local Qwen3 real probe diagnosis and remediation — October 15, 2026

- [x] Participant pulled `qwen3:4b-instruct` (2.5 GB) on Ollama 0.40.4, verified host Ollama `/api/tags` and Docker-host API connectivity. Windows Git checkout fast-forwarded and Docker API rebuilt without errors.
- [x] Participant ran the first 4 deterministic FewRel validation examples against the actual local Qwen model: **4 model calls, 0 emitted claims, 0 review tasks, 0/4 directed head/tail pairs**. Offline grammar on the same four examples also emitted 0 claims. This is observed behavior, not proof that every target relation is directly entailed by its sentence.
- [x] Diagnosed that the full Candidate JSON schema exposes many unneeded fields to the small local model; compact schema and clear non-SVO extraction instructions now used **only** for Ollama. Bedrock's schema unchanged.
- [x] Guarded false deterministic grammar predicates of the form `is a/an/the...`, preventing copular noun phrases from blocking semantically grounded local-model candidate review.
- [x] Added `--diagnose` on the capped 4–6-sample local FewRel probe. It exposes raw model JSON, model review outputs, any rejections, and persisted claims **only when explicitly requested**. No production API trace is enabled by default.
- [x] Mocked end-to-end positive and negative provider review paths now have regression tests. GitHub-hosted code and actual FalkorDB CI passed after fixes. **Actual Qwen before/after improvement remains to be remeasured on the participant laptop**.


## Conservative batch-review milestone — October 15, 2026

- [x] Used participant's actual local-model diagnostic output to isolate **8 model calls** and the 4-call-per-sample cap as the cause of at least one skipped semantic review; 4 claims were accepted across 2/4 FewRel examples, but 0/4 annotated directed pairs matched.
- [x] Identified two semantic soundness hazards in accepted claims: ambiguous agent for a trailing 'entering into' clause; n-ary 'situated between A, B and C' degraded into individual binary claims. A source-quote typo (`Adri-atic`) was correctly rejected and remains a rejection, not an automatic quote rewrite.
- [x] Replaced local Ollama's per-candidate sequential semantic-review calls with one **typed indexed batch** of up to 12 unresolved candidates per chunk. Grammar and structured input remain deterministic; Bedrock unchanged. Batch omissions/duplicates and overflow candidates produce review tasks.
- [x] Implemented conservative deterministic guard for n-ary between and ambiguous participial subject attachments.
- [x] Added targeted `tests/test_batch_review.py`, migrated Ollama mock tests and fixed issues caught by hosted CI.
- [x] [CI run 38702438378](https://github.com/divyashy20-boop/graph-hacks-2026/actions/runs/38702438378) passed **86 non-integration tests and 2 live FalkorDB integration tests** with synthetic and external offline evaluation. Actual post-change Qwen inference remains untested.
- [ ] Rerun the same four source examples with the participant's local Ollama model and inspect claim/review trace. Do not make an extraction accuracy claim until new empirical results and human adjudication are available.


## Real Qwen batch-run findings and spatial normalization — October 15, 2026

- [x] Participant supplied live Qwen diagnostic after batch change: same 4 FewRel samples, 8 to 5 local model calls, accepted claims 4 to 1, review tasks 2 to 5, and head-tail pair hits stayed 0/4. Exact quote check remained 1/1 for accepted post-batch claims.
- [x] Confirmed previous ambiguous participial-entry claim and flattened BETWEEN relations now abstain, while an explicit LOCATED_IN relation remains accepted.
- [x] Identified a false negative from the local model semantic reviewer for explicit *just south of*; reviewer incorrectly rejected SITUATED_JUST_SOUTH_OF despite source wording. Added generalized directional spatial predicate normalization to base NORTH/SOUTH/EAST/WEST_OF, retaining source quote and requiring standard semantic review.
- [x] Added tests for direction variants and negative/spatial verification; CI run 38704185238 was green with real FalkorDB integration.
- [ ] Rerun *new* spatial normalization on the participant's real local model; no actual post-change accuracy claims.
- [ ] Annotate an independent source-supported relation set (not FewRel pair labels alone), with negative controls and linguistic group relations.

## Milestone B recovery and completion — October 15, 2026

- [x] Inspected status, tracked diffs, every pending new module/fixture and base
  `487435f9df92a472a4ad38f29ce970f11a4da1a2`. Preserved all interrupted work;
  no reset, replacement implementation or graph-volume removal.
- [x] Recovered date extraction/deduplication, provisional evaluation, public
  annotation preparation and shared-engine incident/supply/research demos.
  Completed dashboard assets, evidence/timeline/identity inspection, labelled
  query results, real authorized investigations, saved cases and review queue.
- [x] Correctness follow-up: dates tied to the matching grammar relation, not
  unrelated earlier sentences; wrong event-time/historical flags vetoed;
  event/graph year/month/day filtering consistent. Context changes clear UI
  authorization, result panels and idempotency state. Versioned assets prevent
  old dashboard scripts surviving an update. Added regression coverage.
- [x] Final local suites: **126 non-integration + 4 actual FalkorDB = 130 passed**,
  no failed/skipped tests; one TestClient deprecation warning. JavaScript syntax,
  Python compilation, targeted Ruff and Docker packaging checked. Actual graph
  tests use isolated random namespaces and clean only their own graphs.
- [x] Reran frozen provisional evaluation: 6/8 binary targets, 6 predictions,
  P100/R75/F1 **85.71%**, four/four whole events, 14/14 roles, surface entities
  25/29, exact quotes 10/10, empty control 1/1. Independent arithmetic cross-check
  confirmed counts/macro93.1973 without evaluator helpers. No claim of independent
  human gold or general real-world accuracy. Two missed final cases not tuned.
- [x] Reran older challenge: 17/25 targets with 19 predictions, F1 **77.27%**;
  five/five empty controls, exact quotes 19/19. Inspected/tiny provisional data
  remains a limitation. Canonical content hash locked across OS line endings.
- [x] Actual Qwen final-code recheck: four local development calls, 1193 input /
  197 output tokens, three binary + one event (also rule-covered), no extraction
  F1 gain, review-document rate25% versus50% in pre-fix observation. Earlier
  four-public-source/five-call probe accepted no claims. Seventeen actual local
  calls across before/after/final development and public probes; cloud$0, local
  compute unmeasured. Human annotations for the24-source public queue pending.
- [x] Real persistent three-domain runner repeated successfully with original
  dataset prefix `showcase-b`: incident/supply each expose two dependencies and
  persist idempotent cases/reviews; role events do not invent binary dependencies;
  research exact-ID overlap RULE_DERIVED in2021, UNKNOWN in2023/name collision.
- [x] Manual browser checks: graph-backed counts, incident query/preview/authorized
  write, supply source-role inspection/query/zoom, research date filter/ambiguous
  identity. API graph+app containers healthy; no paid/cloud services enabled and
  unrelated Khoj infrastructure untouched. Broader browser automation/load/mobile
  certification not claimed.
- [x] Updated README, TEST_REPORT, annotation guide, three-minute DEMO_GUIDE and
  CI checks for frozen evaluation, actual three-domain graph runner, JavaScript
  syntax and packaged Docker API. User directly authorized commit/push of verified
  Milestone B changes to main. Exact pushed SHA and hosted Actions result must
  be verified in the final handoff, not inferred from a workflow file.
- [ ] Independent human adjudication, improved general public-prose coverage,
  recorded video, production hardening/public deployment, paid provider validation.
  None is represented as completed by the passing synthetic/test suites.

## Milestone C — conversion accuracy and reliability gate, October 15, 2026

- [x] Continued verified B `4799c328f0c4cfdfd611390afa07042ffbc1ce08` in the
  existing repository; inspected history/status and preserved every interrupted C
  change. No replacement project, force/reset, source-mirror edits or paid service.
- [x] Inspected original24-source FewRel queue and excluded4 already-inspected
  sources. Prepared source-attributed14-case provisional development and23-case
  unreviewed frozen evaluation partitions. Preserved public URLs, licence terms,
  locators, exact text/excerpt hashes and spans. Frozen canonical hashes are in
  `c_manifest.json`; lexical overlap guards are not proof of semantic independence.
- [x] Built full actual-Falkor conversion audit including reconnect payloads and
  exact graph incidence/roles, separate binary/qualified/event/role/surface/pair
  metrics, domain/failure categories, abstention/review observations and timings.
  Unreviewed/incomplete cases never become empty gold. Human-edit promotion writes
  a new version and validates declarations/provenance; no human labels fabricated.
- [x] Before fixes, mixed provisional binary2/3/15,F122.22%; after4/4/15,F142.11%.
  Public-only complete subset remains weak:1/1/12,F115.38%,recall8.33%. Whole
  public research event0/1 and roles0/4. Entity surface F136.36%->45.71%, not
  exhaustive NER. Exact quotes5/5 final do not establish semantic correctness.
  Added standalone independent arithmetic recheck without scorer-helper imports.
- [x] Focused general regressions: bounded appositive/main-clause recovery,
  numeric names/determiners; modal negation; strict temporal tails and declared
  precision; whole-word entity/attribution grounding; structured preflight before
  any document writes; malformed PDF/JSON/CSV safety; canonical OWN/USE aliases
  and legacy read comparisons. No dataset-specific entity lookup or relaxed model
  evidence gate. Candidate-free chunks explicitly disclose unassessed completeness.
- [x] Older synthetic20 retains22/24,F195.65%; B12 retains6/8,F185.71%,4 events,
 14 roles. Prior26 challenge17/19/25->17/18/25,F177.27%->79.07%: one attributed
  false acceptance removed. Fixed evaluator gold normalization to apply the same
  canonical aliases as predictions; no gold edits/threshold reductions.
- [x] Actual Windows Ollama Qwen probes, not mocks: matched4 public dev sources,
  baseline4calls/0claims; latestfinal5calls/3claims/2reviews, exact1/3/9,F116.67%.
  Rules alone on identical sources1/1/9,F120%; no extra exact recall. Two accepted
  predicates omit provisional building qualifiers; supported preparing-for-launch
  candidate wrongly rejected by reviewer. Prior reruns differed; latest observation
  retained, not best-run cherry-picking. Raw intermediate traces not all retained.
- [x] Frozen final checkpoint, after extraction fixes:23 offline sources,0claims,
 46 records/23 incidence edges consistent; four-source Qwen probe6calls,2 accepted
  unassessed claims,6reviews,2/2 quotes. All frozen sources remain unreviewed, so
  no F1 or hallucination/correct-abstention rate. Published C model reports retain
 15 calls; other bounded development probes ran too. Cloud$0, local compute unknown.
- [x] Actual CSV/JSON100/1000/2000 capacity measurements:100 passes both formats;
  1,000 and2,000 time out despite fitting quotas, fresh graphs empty afterwards.
  Separate actual graph rollback test protects seeded existing data. Measured
  client allocation/CPU/write/query/duplicate/repeat/reconnect behavior. No p95,
  server CPU/RSS or scalability promise. HTTP503 explains execution budget failure.
- [x] Tried a bounded single-query bulk-writer optimization on isolated test
  graphs. Real integration checks caught label/payload/persistence failures;
  rejected it and restored `ugi/store.py` byte-for-byte. Known-good writer retained;
  capacity issue not hidden with longer timeout or partial-document commits.
- [x] Actual public one-page NASA PDF ingestion and rendered visual inspection,
  one claim/two entities/exact quote. Not a multi-column or OCR benchmark;14.3MB
  newsletter exceeds quota and was not ingested. Download/render remain ignored.
- [x] Full local suite169 passed (162 non-integration +7 real FalkorDB),0 skipped
  or failed; existing TestClient deprecation remains. Three actual persistent demo
  domains rerun idempotently. Python/JS syntax and new-file lint checked. Updated
  README/TEST_REPORT/DEMO_GUIDE/annotation protocol and added CONVERTER_AUDIT and
  source-specific DATA_LICENSES. CI now verifies source-aware real graph audit,
  frozen unreviewed checkpoint, arithmetic and100-record capacity, no model calls.
- [ ] Independent human adjudication and reliable full public-prose/event recall.
- [ ] Safe atomic bulk-write scaling at1,000/2,000 under existing resource budgets;
  do not mistake validation quota for demonstrated throughput.
- [ ] Broad PDF layout/OCR, production/security/load certification, public hosting
  and paid provider validation. User volumes and unrelated Khoj AWS untouched.
- Delivery gate: final commit/push and hosted Actions conclusion must be verified
  for the delivered SHA and recorded in the handoff; local test success/workflow
  text alone is not hosted CI evidence.
- [x] Final combined rerun169/169 passed; independent arithmetic counts match
  (floating-point F1 equality uses1e-12 tolerance). Docker API rebuilt/healthy.
  Packaged HTTP smoke passed: two opposing claims,422 malformed upload/no graph
  mutation, CONTRADICTED query, duplicate upload and dashboard asset. Initial
  singular endpoint typo produced404 and was corrected to `/api/relationships`;
  removed only both owned synthetic test graphs after verification.

## Milestone D increment 1 — October 16, 2026

- [x] Read requested documentation/code, verified clean C base2a0a5df and remote
  main, checked actual Docker/FalkorDB/Ollama. No user work discarded or cloud used.
- [x] Recorded fresh unchanged C actual-graph/model baselines before changes.
  Offline stage diagnosis:11 missing binaries +1 whole event never proposed;
  entity recognition cannot be independently isolated (no distinct NER stage).
- [x] Added bounded occupation/organization appositives and responsibility/action/
  purpose lists. Preserved historical, negative/possible scope, full exact evidence
  and whole events; ambiguous attachments fail closed. No benchmark-entity lookup.
  No large NLP dependency justified for this measured bounded improvement.
- [x] Source-only exact-offset surface hints inform local model prompts. Actual
  first probe exposed partial-quote predicate/history escape and omitted occupation
  interval. Added enclosing grammar and pair-anchored date guards; preserved first
  probe report. Same-model review remains fallible, not independent truth.
- [x] Same public complete development1/1/12 ->7/7/12,F1 15.38% ->73.68%; mixed
 4/4/15 ->10/10/15,F1 42.11% ->80%; entity surfaces F1 71.43%, not NER. Public
  research event0/1/roles0/4; finance/spatial incomplete/unscored. No frozen C tuning.
- [x] Actual local model4-source comparison: baseline4calls/1claim; final5calls/
 8claims/11reviews,7/8/9 exact,F1 82.35%. Rules same subset7/7/9,F1 87.5%; no
  extra exact model recall. First6-call probe retained, total15 calls/$0 cloud.
- [x] Full186 passed including7 actual FalkorDB; original20/B12/challenge26 counts
  unchanged; independent arithmetic, targeted lint and source hashes checked.
  C appositive test now expects added affiliation AND the preserved main clause;
  no gold/accuracy targets relaxed. Host URL environment initially polluted one
  mock endpoint test; cleared before successful full rerun, not changed expectation.
- [x] Updated diagnosis/audit/README/TEST_REPORT and created MILESTONE_D_REPORT;
  safe graph-write investigation is explicitly a subsequent increment. Store
  remains unchanged until this increment is tested/committed and CI checked.
