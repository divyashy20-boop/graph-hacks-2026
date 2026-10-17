# Final coverage matrix

| Topic | Actual test | Acceptance |
|---|---|---|
| Real pinned sources | Five GitHub Compose files parsed and ingested by original UGI Engine into isolated FalkorDB namespace | 5 source SHA checks + 5 graph persist checks |
| Rulebook MCP | 10 original and 39 expanded actual JSON-RPC/MCP workflows | 49 exact investigation completions, no model fabrication |
| Graph reasoning | 26 examples incl direct, reverse and transitive; explanation/claim consistency | no unsupported positive proofs, no RULE_DERIVED contradiction |
| Model comparison | Original model-selected legacy Qwen and nonbinding advisor | diagnostic only; separately FAIL/INCONCLUSIVE, not a hidden pass |
| P5 SQLite temporal store | 83 previous tests + 17 scenarios | P5 synthetic tests all pass |
| Bridge offline | Real UGI in-memory backend and actual JSON-RPC MCP handler; plus adversarial fake transport | 28 initial new tests; conflict UNKNOWN, negative read invalidation, durable registry, no external side effects |
| Bridge live | Actual UGI Engine backed by new FalkorDB graphs, MCP stdio, P5 SQLite sidecar | real new dependency invalidates old absence; actual contradictory assertion => UNKNOWN; internal action blocks |
| Multi-agent propagation | Captured MCP parent receipt, 2 downstream derived receipts, source observation update | both descendants STALE |
| Provenance integrity | Untrusted params, entity identity, claim sources, registry tampering | rejected/fail closed |
| H1 safety | Source-hash preflight compares host and running API container; original file hash after run | no stale image certification or on-disk modifications |
| True external AWS action | Not executed | Requires actual coordinated executor and security review before enabling |
