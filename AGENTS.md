# Repository instructions for implementation agents

This is the **October 15–18, 2026 event-time** Universal Graph Intelligence package; the historical UniversalGraphConverter prototype is not included. Maintain accurate provenance and do not represent pre-event code as event-time implementation.

- Work in `event/` and preserve working `ugi/` and `tests/` modules.
- Core semantics: exact source evidence is needed for SOURCE_ASSERTED/SOURCE_NEGATED; CONNECTED_ONLY is not proof; RULE_DERIVED requires a sound explicit rule; HYPOTHESIS remains separate from Claim. Never silently turn an uncertain graph edge into a fact.
- Writes require explicit authorization. MCP actions require both request `authorise_action=true` and process `UGI_MCP_ALLOW_WRITES=1`. Never expose arbitrary Cypher execution to external users.
- Production/demo persistent graph backend is FalkorDB; in-memory is only for tests. Do not claim a mocked test is a live graph integration.
- Prefer tightly scoped code changes and regression tests over broad literature review. Keep model spend disabled unless user explicitly authorises it.
- Commands: `python -m pytest -q`, `python -m ugi.evaluate --output evaluation/my_report.json`. Real integration requires `UGI_TEST_REDIS_URL` and a live FalkorDB server.
- Before submission: re-test Docker, compare against genuinely unseen annotated data, independently verify model and graph integrations, and disclose remaining limitations.
- Never modify the unrelated Khoj/Bharat Talaash AWS infrastructure or commit `.env` files.
