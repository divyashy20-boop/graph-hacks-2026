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
