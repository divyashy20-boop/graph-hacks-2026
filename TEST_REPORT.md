# Verified follow-up report — October 15, 2026

This report describes the **ChatGPT continuation** of the event implementation supplied as `event.zip`. Prior Codex outputs are clearly distinguished from what was actually reproduced here.

## Code quality and functionality

- Recovered project contained 36 passing functional/API/provider tests and 1 integration test requiring an external FalkorDB service.
- Current project: **47 passed, 1 skipped, 0 failed**, executed in Python 3.13.5 with `pytest` 9.0.2, FastAPI 0.128.2, Pydantic 2.13.5 and local in-memory storage.
- `ugi/mcp_server.py`: typed, bounded MCP JSON-RPC stdio tools added. Handshake, tool listing, read-only evaluation, citation retrieval, write opt-in, actual stdio subprocess all passed locally. Full compatibility with third-party MCP clients not established.
- Python `compileall` completed without syntax errors.
- Real FalkorDB was **not** independently tested in this environment: no Docker engine or Redis driver was available. The missing Redis import was bridged by an **external temporary test-only import shim**, not included in the deliverable. All passing results involving graph writes here used the project's in-memory test backend. This distinction must not be removed from future demo statements.
- No live Bedrock calls, no paid inference, no AWS deployment.

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
