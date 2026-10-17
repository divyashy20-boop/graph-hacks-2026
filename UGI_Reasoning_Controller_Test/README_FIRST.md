# UGI Reasoning Controller — isolated rulebook experiment

## Why this package exists

UGI's original local Qwen workflow failed at the first tool stage (0/10 strict runs), often supplying `service_name`, `service`, or `field` rather than the MCP `search_entities({"name": ...})` schema. This experiment moves control of **tool choice, argument construction, verification and actions** from free-form model output to a short, explicit, inspectable Python rulebook.

**This is a guided deterministic controller, not yet a general autonomous agent.** It optionally asks local Qwen for tool recommendations, but its advice is nonbinding. The report records model advice accuracy **separately**, so a passing guided workflow does *not* get mislabeled as independent Qwen planning. This tradeoff is intentional.

## Input and data

Five real (developer-authored) Docker Compose examples from `docker/awesome-compose`, pinned to commit `30f4b7f6a6c3b0c0ecf4d4efb0de203c48d11562`. SHA256-verified snapshots already included (no internet access required). The source manifests are converted into explicit JSON `DEPENDS_ON` triples; this does not prove arbitrary YAML ingestion, natural language extraction, causation or real outages.

## Safeguards

- Windows needs **Docker Desktop**, not a host Python installation.
- Existing UGI source code, Milestone H1 changes and existing datasets/volumes are NOT modified. Copied UGI code and patched engine stay under Docker `/tmp/ugi_rulebook_hotfix/`.
- New graphs use randomly generated `ugi_real_*` namespaces and are **retained** for inspection, not deleted.
- MCP server environment explicitly sets `UGI_MCP_ALLOW_WRITES=0`. Even requested investigation previews must include `authorise_action: false`. No external actions or paid API calls.
- Source citations verified by exact claim/source/evidence IDs; no fabricated or LLM-provided claim IDs are sent to MCP.
- Unknown, unsupported or ambiguous requests abstain; unsafe requests do not reach the MCP tools.

## Windows running steps

1. Place `UGI_Reasoning_Controller_Test.zip` in Downloads.
2. Extract it into UGI's `event` repository root (same directory as `compose.yaml` and `ugi/`).
3. In PowerShell, from the `event` folder:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File '.\UGI_Reasoning_Controller_Test\START_RULEBOOK_TEST_WINDOWS.ps1'
```

Optional flags:

- `-SkipLLM` — run deterministic controller and graph tests without Ollama calls.
- `-RunLegacyAgent` — also rerun the original unconstrained LLM-selected agent for a **fresh** side-by-side contrast. This may take longer.
- `-OllamaModel 'qwen3:4b-instruct'` — choose a different installed model.

## Results

`UGI_Reasoning_Controller_Test/results/rulebook_result.json` has workflow-by-workflow MCP traces, observed graph statuses, exact claim IDs and source-quote hashes; `patch_receipt.json` shows code checksums. A nonzero exit indicates a failed check; reports should still be copied where possible.

## Interpretation

A PASS demonstrates this **narrow, rulebook-driven** service-dependency workflow can finish its checklist against actual FalkorDB and UGI MCP. It does not establish arbitrary autonomous task planning, broad NLP, real incident causality, crash-safe concurrent snapshots, full Track 2 recomputation, or external Jira/Slack actions. Tests must not be misrepresented as those capabilities.

## Next steps if guided mode passes

Add a real schema-constrained LLM intent interpreter for tasks without explicit named entities, with bounded recovery that never silently supplies correct benchmark answers; then test on new, independently labeled tasks. Integrate into production only after code review and separate regressions against the latest H1 work.

## v2.1 packaging fix (October 17)
The previous Rulebook ZIP accidentally bundled an older engine patcher. It expected
`return` and `"rules": ["shared_employer_temporal_overlap_v1"]` on the
same line, but the actual UGI app puts the shared-employer rule on its own line.
This re-package includes the **previously successful** Agent Fix v2 patcher,
a split-line regression test and a preflight patch-version check.
Only `/tmp/ugi_rulebook_hotfix/ugi` is patched at runtime.
Extract ZIP with `-Force` over the prior test folder; the original UGI
source and uncommitted H1 changes remain untouched.
A green offline result does not imply live FalkorDB or Qwen has passed.
