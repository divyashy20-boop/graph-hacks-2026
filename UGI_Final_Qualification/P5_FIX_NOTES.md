# P5 surgical qualification fix (v1.2)

Previous real FalkorDB+MCP+P5 run: **9/11**, two failed checks. This package
changes only the **isolated qualification implementation**, not UGI host source.

## Fixed

1. In `p5memory/core.py`, status changes are **monotone** with safety priority
   `VALID < STALE < UNKNOWN`. An original plan already STALE may become UNKNOWN
   on a newly confirmed conflict, but neither status can revert to VALID.
2. In `ugi_final/bridge.py`, freshness diagnostics compare all recorded field
   fingerprints against the **original sealed receipt**, not just the number
   of new writes during the current refresh. When another receipt rereads a
   shared MCP tool first, our refresh can write zero new changes even though
   our original read-set is different. A prior STALE remains STALE.
3. The **same eleven real combined checks** are kept. The unrelated-receipt
   check now uses original-read differences; the contradiction test expects
   UNKNOWN even when receipt was previously STALE. An extra actual-UGI-memory
   test confirms an unrelated graph assertion leaves a genuinely unrelated
   answer VALID.
4. Separate focused Windows runner `START_P5_FIX_WINDOWS.ps1` reruns P5
   regressions, real UGI Engine/MCP handler unit tests and the **11 real
   FalkorDB/MCP combined cases** in disposable namespaces; no need to repeat
   the already-green 49 guided workflows or legacy Qwen comparison.
5. `ugi_final/focused_report.py` requires exactly eleven named live checks;
   missing/duplicated cases cannot yield a false go decision.

## Run

```powershell
$repo='C:\Users\Divyash\Downloads\Universal_Graph_Intelligence_Updated_2026-10-15 (2)\event'
Set-Location $repo
Expand-Archive -LiteralPath "$env:USERPROFILE\Downloads\UGI_Final_P5_Surgical_Fix.zip" -DestinationPath $repo -Force
powershell -NoProfile -ExecutionPolicy Bypass -File '.\UGI_Final_Qualification\START_P5_FIX_WINDOWS.ps1'
```

Outputs: `UGI_Final_Qualification/results/p5_fix_<runid>/P5_FIX_DECISION.json`
and `combined_graph_memory.json` and `patch_receipt.json`.

**This is NOT deployment authorization.** Uninstrumented graph reads, external
TOCTOU/fencing, production persistence/authorization, H1 unseen NLP and the
actual UI/API integration remain open. A green result qualifies the feature
for **feature-flagged integration testing only**.
