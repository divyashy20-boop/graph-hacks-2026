# UGI All-in-One Guided Agent Audit — v3.0

## Read first

**No production integration, no existing graph changes, no paid AI API.** The script operates in disposable `/tmp/ugi_all_hotfix/` Python code and UUID-prefixed `ugi_real_*` FalkorDB graphs. New test graphs are retained for review, never deleted. Existing H1/working-tree files and Docker volumes are not removed or overwritten.

This is a **guided deterministic state machine**, not proof of a general autonomous agent. Qwen may advise on tool selection; its advice does not control execution. The rulebook is only supported for narrow service-dependency questions. The new cases extend that bounded coverage; all five datasets are **real pinned Docker Compose examples** transformed into structured JSON, not production outage ground truth or arbitrary NLP extraction.

## One-command run on Windows PowerShell

Download `UGI_All_In_One_Stress_Test.zip` to Downloads. Paste:

```powershell
$ErrorActionPreference = 'Stop'
$repo = 'C:\Users\Divyash\Downloads\Universal_Graph_Intelligence_Updated_2026-10-15 (2)\event'
$zip = "$env:USERPROFILE\Downloads\UGI_All_In_One_Stress_Test.zip"
if (!(Test-Path $zip)) { throw "ZIP missing: $zip" }
Set-Location $repo
Expand-Archive -LiteralPath $zip -DestinationPath $repo -Force
powershell -NoProfile -ExecutionPolicy Bypass -File '.\UGI_All_In_One_Test\START_ALL_TESTS_WINDOWS.ps1' -RunLegacyAgent
```

Prerequisites: UGI Docker Compose services `graph` and `api` already running; optional `qwen3:4b-instruct` in host Ollama. No Windows Python installation needed.

**Faster graph-only run** (no Ollama, but all rulebook/graph/security tests):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File '.\UGI_All_In_One_Test\START_ALL_TESTS_WINDOWS.ps1' -SkipLLM
```

`-RunLegacyAgent` performs a fresh 10-question unconstrained Qwen baseline. If model is unavailable, that category reports INCONCLUSIVE. The main guided and extended real MCP checks still run.

## What is new in v3

- **70 offline unit tests**, including 16 new test methods with 25 unsafe command variants, new parser synonym and reversed-grammar cases, ambiguous and temporal requests, server schema drift, wrong source provenance and action refusal.
- **49 live MCP workflows planned:** original 10 multi-step investigations with evidence and read-only previews, plus 39 new tests including unknown/reverse links, explicit positive dependencies, derived reachability, `rely on` and `required by` grammar. The 39 extra tasks do not preview unless requested.
- Model advisory selection is scored separately from successful controller execution; the baseline is separate and cannot make controller outcomes green.
- **New strict provenance gate:** positive claim source IDs must match the expected data source for the selected dataset.
- **Actual MCP schema enforcement:** validates required keys, server field types, lengths, and `additionalProperties=false`; no model-argument substitution.
- Rejects unsupported causal, temporal, negated, ambiguous and unsafe requests instead of quietly inventing answers.
- Verify host `ugi/engine.py` hash before/after; patch only copied engine in Docker `/tmp` with v2 guarded patcher.
- All 49 are scenarios on five pinned public configuration sources, **not** 49 independent real deployments or real outages.

## Outputs

- `UGI_All_In_One_Test\results\rulebook_result.json` — full results: `workflows` (10), `extended_workflows` (39), evidence and tool traces.
- `UGI_All_In_One_Test\results\patch_receipt.json` — before/after SHA256 in disposable UGI engine, no code install.

All test source examples in `ugi_real_track1/snapshots`. Unit tests, manifests and implementation code are included. If the run exits nonzero, upload the JSON and PowerShell traceback, **do not reset git or delete any Docker data**.

## Query your new isolated test graph after a successful run

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File '.\UGI_All_In_One_Test\RUN_ONE_QUERY_WINDOWS.ps1' -Dataset 'nginx-flask-mysql' -Query 'Does proxy indirectly depend on db?'
```

Single-query results are saved to unique JSON files in the `results` folder. Requests beyond narrow relationship semantics will abstain. They are never routed to an existing production dataset.

## Scope and limitations

Passing tests only establish supported rulebook behavior on these tasks, pinned source declarations, and actual read-only MCP/FalkorDB if run on Windows Docker. Arbitrary natural language extraction, production outages, independent incident labels, performance at scale, distributed transaction isolation, persistent semantic recomputation, autonomous dynamic planning, and external Jira/Slack/email actions are **not established**. Do not interpret Qwen advisory disagreement as an execution failure of the guided controller, or deterministic controller completion as independent LLM autonomy.


## v4 hotfix (critical)
The v3 live report failed 0/49 due to a Python **stale-module import**.
`python -m` was executed from `/tmp`, which can contain an older
`ugi_real_track1/real_suite.py` lacking `prepared[dataset]["source_id"]`.
All test code now executes with working directory `/tmp/ugi_all_in_one_pkg`,
and a preflight asserts exact module paths including the patched engine.
Provenance cannot be silently omitted; missing source IDs abort early.
Tests for deliberately shadowed modules now included. Original UGI untouched.
Results from a previous v3 run are not a valid evaluation of the v4 controller.


## v5: Docker temp permission fix
The v4 runner stopped on `rm: Permission denied` when trying to delete root-owned
files from a previous `docker cp`. v5 **never deletes or chmods old test directories**.
Every run uses a fresh UUID-namespaced temporary path and records it in
`results/runtime_paths.json` for `RUN_ONE_QUERY_WINDOWS.ps1`.
No UGI application source, Docker volume or existing graph is intentionally changed.
Old temp package directories are left untouched (small, disposable files).
This fix is structurally tested offline; live Docker execution is not verified here.
