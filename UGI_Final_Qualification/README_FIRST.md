# P5 surgical fix v1.2 — start here

The last full qualification passed the original 49 guided MCP workflows and
17 local memory scenarios, but the combined 11 real FalkorDB/MCP/P5 cases
had two failures. **Use the focused retest**, not another expensive full run.

See **P5_FIX_NOTES.md** and execute `START_P5_FIX_WINDOWS.ps1` after extracting
`UGI_Final_P5_Surgical_Fix.zip` next to `ugi/` and `compose.yaml`.

The original `START_FINAL_WINDOWS.ps1` remains available if a full post-fix
qualification is desired after the focused run. No permanent UGI source
changes or AWS deployment are made by either script.

---

# UGI FINAL qualification suite (2026-10-17)

**Purpose**: Final pre-merge qualification, not a production deployment and **NOT a permanent integration**. The previous V5 controller and P5 SQLite lab are embedded. A NEW bridge exercises actual UGI Engine + MCP + P5 receipts, including mutation of newly created **disposable FalkorDB graph namespaces**.

## Run on Windows, no local Python required

Save `UGI_Final_Qualification.zip` to Downloads. Extract it into your existing **event** directory (same directory as `ugi/` and `compose.yaml`), then run:

```powershell
$ErrorActionPreference='Stop'
$repo='C:\Users\Divyash\Downloads\Universal_Graph_Intelligence_Updated_2026-10-15 (2)\event'
Set-Location $repo
Expand-Archive -LiteralPath "$env:USERPROFILE\Downloads\UGI_Final_Qualification.zip" -DestinationPath $repo -Force
powershell -NoProfile -ExecutionPolicy Bypass -File '.\UGI_Final_Qualification\START_FINAL_WINDOWS.ps1'
```

Default runner attempts the optional Qwen tool-advice & legacy model comparison; *these are separately reported and are not expected to pass*. To save time, add `-SkipLLM`. To run the optional original UGI pytest tests, add `-IncludeNativeUGITests` **only if** pytest is already installed in the container (the production Dockerfile does not install pytest). The core suite already invokes the actual UGI Engine and MCP handler in unit tests, plus actual FalkorDB over stdio in live runs.

Preconditions: Docker Desktop running, `docker compose up -d graph api` done earlier, and API container's six critical source files exactly match those on host. If it detects H1 unbuilt changes, the runner refuses to test stale Docker code; it will **not rebuild** automatically.

## Reports

Each execution gets a distinct local results folder: `UGI_Final_Qualification/results/<runid>/`.

- `FINAL_DECISION.json`: decisive phase PASS/FAIL and unresolved integration boundaries
- `rulebook_result.json`: 10 original plus 39 additional *live* FalkorDB/MCP workflows, 26 direct graph checks, optional Qwen 0/10 historical comparison retest
- `p5_lab_report.json`: 17 SQLite synthetic P5 scenarios
- `combined_graph_memory.json`: new actual FalkorDB -> actual MCP -> Rulebook -> automatic P5 receipt capture, new edge vs negative read, UNKNOWN conflict, action gating and multi-agent dependency cascade
- `patch_receipt.json`: guarded explanation fix in ephemeral copy ONLY

**Upload `FINAL_DECISION.json`, `combined_graph_memory.json`, and the final PowerShell output**. If a phase fails, we will have exact failure and can decide integration versus skipping that capability. Never decide from an overall score without checking required phases.

## Testing boundaries, no inflated claims

1. All online graph test data are SHA256-pinned genuine Docker Compose declarations in `docker/awesome-compose`, transformed by strict parsing into JSON assertions; **not live incident telemetry or native natural-language interpretation**.
2. The controller is a deterministic policy state machine. Optional Qwen advice is nonbinding and free-form LLM tool choice remains weak.
3. P5 captures tool outputs automatically when all calls go through `CapturingMCP`. The registry persists in local SQLite and verifies checksums, but **full coverage across every deployed endpoint and distributed restart/replay are not yet proven**.
4. The P5 SQLite gate blocks stale or UNKNOWN **internal test effects only**. It is not atomically coordinated with the external FalkorDB or AWS services. Real-world external action atomicity and TOCTOU require a coordinated outbox/revision-fence executor.
5. Changes written outside the instrumented path are detectable at the **mandatory reread before reuse**; without reread they can be missed. A graph change *after* reread can still race an external action; this suite does not certify otherwise.
6. This suite creates entirely new graph namespaces and leaves them intact for inspection; it never runs `GRAPH.DELETE`, writes to existing namespaces, touches graph volumes, patches on-disk `ugi` code or deploys to AWS. It uses read-only preview paths for investigation actions.
7. Problem 1's full versioned profile-card / undo infrastructure, H1 open-domain NLP, arbitrary unseen-world truth, broad temporal semantic disambiguation, scale/concurrency across distributed services, and AWS security reviews are **not established by the bounded benchmark**.

## Decision rule

All mandatory unit suites + engine patch-copy validation + 49 Rulebook live cases + 17 P5 scenarios + real MCP-to-P5 combined cases must pass. Known poor Qwen advisory/baseline results appear as **non-gating FAIL**, never hidden or converted into success. A green result means **qualified for feature-flagged implementation/integration test**, not AWS-ready.

Note: The original UGI `engine.py` explanation patch is applied to a temporary Docker copy. Merging is a separate reviewed step after test qualification.
