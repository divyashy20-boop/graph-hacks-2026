# UGI Problem 5: Dynamic Knowledge & Agent Memory Receipts (standalone proof)

**Status: experimental; do not integrate or claim production protection yet.**

This lab implements bitemporal knowledge events, automatically captured exact-field and scoped-negative read sets, versioned agent-output receipts, reverse dependency indexing, conflict/unknown labels, cascading invalidation, an atomic internal pre-action gate, JSON field diff and Python AST signature diff.

It is a reproducible **synthetic SQLite reference**, NOT a FalkorDB / real UGI application integration or proof of distributed/external action atomicity. No LLM required and no paid APIs.

## Windows (Docker; no Windows Python installation needed)

Unzip **the whole `UGI_Memory_Receipts_Lab` folder** inside the `event` UGI repo. Ensure your original `api` Docker service is running (`docker compose up -d`). In PowerShell:

```powershell
$repo = 'C:\Users\Divyash\Downloads\Universal_Graph_Intelligence_Updated_2026-10-15 (2)\event'
$zip = "$env:USERPROFILE\Downloads\UGI_Problem5_Dynamic_Memory_Lab.zip"
Set-Location $repo
Expand-Archive -LiteralPath $zip -DestinationPath $repo -Force
powershell -NoProfile -ExecutionPolicy Bypass -File '.\UGI_Memory_Receipts_Lab\START_MEMORY_TEST_WINDOWS.ps1'
```

Results saved to `UGI_Memory_Receipts_Lab/results/p5_lab_report_<runID>.json` and `p5_lab_report_latest.json`.
Each run gets unique Docker `/tmp` paths to avoid previous permission/stale-import bugs. No Docker volumes, UGI source, existing graphs or H1 files are modified.

## Linux / local Python

```bash
cd UGI_Memory_Receipts_Lab
sh RUN_LOCAL_LINUX.sh
```

Uses only Python standard library; SQLite file is inside a temporary directory and disposed after each test run.

## How it works

- `Memory.publish` / `batch_publish` append assertions and retractions with both valid-time intervals `[from,to)` and monotonically increasing knowledge revisions.
- `Reader.read(key, field)` captures a fine-grained positive **or absent** field read without trusting the agent to enumerate dependencies.
- `Reader.scan(prefix)` captures a **query predicate/read scope** so new matching facts invalidate conclusions previously based on empty results.
- `Reader.seal(output, parents=...)` creates an immutable output receipt and reverse lookup links. If the graph changed during reasoning, the receipt starts `STALE`. If a read was conflicted, starts `UNKNOWN`.
- Every relevant fact change marks outputs `STALE` / `UNKNOWN` and cascades downstream; outputs are *never silently re-approved*. Replanning must create a new receipt.
- `protected_action(...)` is an atomic **internal SQLite-only effect**, serializing revalidation, receipt status checks and effect insert in `BEGIN IMMEDIATE`, including idempotency.
- `sweep(day)` handles expiry even without incoming events.
- `ingest_python(...)` uses AST for top-level functions and class methods; changed signatures are atomic updates. It does **not execute code**.
- `ingest_json(...)` flattens object leaves into escaped JSON Pointer fields and processes deletions as source-scoped retractions. Arrays are conservative atomic values.

## Pass criteria

All unit/security/race tests must pass, all 17 scenario assertions must pass, no blocked internal action should create a `protected_effects` row, no old receipt should become automatically `VALID`, and original host `ugi/engine.py` SHA256 must be unchanged.

**Limitations, which a passing report does NOT eliminate:** Source truth and evidence verification remain upstream responsibilities. `Reader` only records facts read through it; arbitrary LLM context, caches and other tools are not captured yet. External writes to AWS, shell, GitHub, payments or real incident response are **not** atomic with SQLite and this library deliberately implements none. The design needs a real graph revision/checkpoint contract, transaction fence for external effect consumers, comprehensive automatic MCP/query interception, concurrent/distributed-scale testing and genuine external benchmarks before production integration.

## Decision

If this reference lab passes, it is evidence that the *local algorithm* for receipts and staleness is sound on tested cases. The next decision should be to test a **read-through UGI MCP adapter in a disposable real graph**. Do not claim actual integration or unlimited-scale memory from this package.
