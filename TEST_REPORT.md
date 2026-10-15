# Verified follow-up report — October 15, 2026

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
