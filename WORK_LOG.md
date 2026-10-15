# Event-time implementation work log

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
