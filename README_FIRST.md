# UGI + Krish (both ZIPs): safe integration test lab

**Status:** experimental read-only sidecar, NOT a production merge or a completed live benchmark. No changes to `ugi/`, no new dependencies, no cloud AI calls, no DB writes. Designed for the verified G-era UGI checkout (`4ae450a...`), with only documented UGI interfaces used.

## What is borrowed/adapted?

| Source | Concept adapted | What this actually tests |
|---|---|---|
| `project1.zip` (`tools.py`, graph algorithms) | Directed PageRank, shortest path, connected components | Bounded graph analytics over UGI claims; excludes negative, uncertain, expired, schema-bound claims; components correctly called *weak connected components* |
| `project1.zip` (`planner.py`, MCP) | Reasoned tool sequence + guardrails | Calls UGI's existing MCP **Python handler**, read-only, and compares with existing investigation **preview**. Not an unconstrained LLM planner or an external MCP stdio interoperability test |
| `graph_hacks_track2.zip` (`gateway/guard.py`, `agents/revalidation.py`) | Freshness before action | Read-only check of UGI's existing `DerivedArtifact` identity-input revision. Stale/unverified -> block; unchanged **identity** inputs does NOT imply all knowledge is current |

Sources are **conceptually adapted**, not blindly copied or executed. The package includes **no original ZIP contents**, `.env`, credentials, model weights, Git history, virtual environments or Node packages. Refer to `SOURCE_MAP.md` for exact source files and checksums.

## Installation on Windows

1. Make a backup or use a throwaway copy of your UGI checkout. **Do not replace files in `ugi/` or remove Docker volumes.**
2. Extract `UGI_Krish_Integration_Lab.zip` **into the root of your latest UGI repository**, alongside `ugi/`, `tests/` and `compose.yaml`. Extraction adds only `ugi_integration_lab/`, `START_TEST_WINDOWS.ps1` and documentation.
3. Open PowerShell in that repository. Activate your existing Python environment. No `pip install` is required beyond UGI's existing dependencies.
4. Run:

```powershell
.\START_TEST_WINDOWS.ps1
```

Expected: 8 bridge tests passed, offline result `PASS`, report `ugi_integration_lab/results/latest.json`. This checks adapted algorithms and safety logic, *not real FalkorDB*.

### Test against current running UGI (no writes)

First confirm **your** existing Docker/FalkorDB services are running and UGI's synthetic `showcase-b-incident` dataset exists. This step uses that dataset **read-only**; it will not seed or delete anything. Unlike normal `ugi.store.Store`, this bridge deliberately bypasses constructor index-creation and blocks write Cypher/commit. Results are best-effort while other processes are writing, not a transactionally isolated snapshot.

```powershell
.\START_TEST_WINDOWS.ps1 -RunLive
```

Expected: live report `ugi_integration_lab/results/live.json`. Check `no_agent_action_written: true`, the baseline preview, the MCP handler trace, and independent analytics. If the graph dataset does not exist or a service is unavailable, it will fail **clearly** without creating data.

If you want a different existing dataset or names:

```powershell
.\START_TEST_WINDOWS.ps1 -RunLive -Dataset "showcase-b-incident" -Start "Checkout" -End "Cache" -Target "Cache"
```

If there is no demo dataset, you may explicitly seed **only synthetic demo data** using the existing UGI command:

```powershell
python -m ugi.demo --dataset-prefix showcase-b
```

**Warning:** The seed command writes synthetic Sources/Claims to named demo datasets even without `--execute`; it does **not** create actions unless `--execute` is included. You do not need to seed if your dataset already exists.

### Test freshness of a previously registered identity-dependent artifact

For an actual existing `DerivedArtifact` ID, run in repository root:

```powershell
python -m ugi_integration_lab.run --mode live --dataset "your-dataset" --start "A" --end "B" --target "A" --artifact-id "your-artifact-id" --output ugi_integration_lab/results/freshness.json
```

The guard **never runs** an action, and it never calls an artifact globally fresh. An ID absent from the dataset returns `BLOCK_UNKNOWN`.

## Interpreting outcomes

- **PASS (offline)**: adaptation code works on its synthetic fixture, including adversarial checks. **Not accuracy proof.**
- **Live path/ranking differs from existing investigation**: may be expected. Krish-style analytics use a conservative `DEPENDS_ON`-only view; UGI's original agent has domain-specific reverse paths and richer logic. Inspect included/excluded reasons before judging.
- **`AMBIGUOUS_OR_MISSING`**: MCP tool handling refuses to assume same-name identities are equal; good fail-closed behavior.
- **`BLOCK_STALE`**: registered entity identity input changed, so downstream artifact must be rechecked.
- **`IDENTITY_INPUTS_CURRENT_ONLY`**: not a full freshness certification; external action remains unauthorized.
- **`search_budget_exhausted` or a read limit error**: insufficient graph coverage to claim a complete answer.

**Known gaps:** No learned LLM tool selection, no dynamic context revalidation, no natural-language extraction accuracy gain, no true community detection, no general code-dependency importer, and no external action connectors. These should not be called integrated until additional real end-to-end tests exist.

## Revert

Just remove the added `ugi_integration_lab/` directory plus `START_TEST_WINDOWS.ps1`, `README_FIRST.md`, and `SOURCE_MAP.md`. The existing UGI source files, graph records and Docker volumes were not modified by the lab.

**Important:** Do not commit this experiment to `main` until the actual live trial and review are successful. Results written under `ugi_integration_lab/results/` may contain user graph data. Keep those local/private.
