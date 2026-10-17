# Provenance and implementation choices

Inputs inspected:
- **Krish #1:** `project1.zip` → `project1/src/universal_graph/tools.py`, `planner.py`, `mcp_server.py`, plus `tests/test_algorithm_tools.py`, `tests/test_llm_planner.py` and `README.md`.
- **Krish #2 / Track 2:** `graph_hacks_track2.zip` → `graph_hacks_track2/gateway/guard.py`, `agents/revalidation.py`, `contracts/models.py`, `contracts/memory_store.py` and relevant docs.
- **UGI:** GitHub `divyashy20-boop/graph-hacks-2026`, verified G-era SHA `4ae450aafe317a945b6f2a04fde1956df6eba568`. Adapter targets `ugi.store.Store`, `ugi.engine.Engine`, `ugi.mcp_server.call_tool`, `ugi.identity.IdentityLedger`, `ugi.models.Settings`.

No source ZIP was re-executed, installed, copied wholesale or joined into the main UGI modules. Adapted algorithms/ideas only.

Differences from Krish #1, by design:
- PageRank excludes claims that fail temporal/polarity/modality/contradiction/provisional restrictions.
- No fuzzy automatic identity merge.
- Centrality is not a real-world risk rating.
- `find_communities` is renamed to **weak components** because it does not discover dense communities.
- BFS has an expansion cap and refuses silently incomplete results.
- MCP planning operates strictly read-only; it does not claim an LLM planned decisions.

Differences from Track 2, by design:
- `current_inputs_only` from UGI checks registered identity revisions, **not** every source fact and code dependency. Never translate that result to globally safe-to-publish.
- No `REVALIDATED` status is invented by appending a dummy note to an old plan; any true semantic re-evaluation remains unimplemented.
- No notification acknowledgements or connector writes.

**Security:** Never include `.env`, `.git`, `.venv`, `node_modules`, source archives, private keys or credentials in this package. No paid calls, no database writes. Test against an isolated dataset when possible.
