param(
    [switch]$SkipLLM,
    [switch]$IncludeNativeUGITests,
    [string]$OllamaModel='qwen3:4b-instruct',
    [string]$OllamaUrl='http://host.docker.internal:11434'
)
$ErrorActionPreference='Stop'
$root=$PSScriptRoot
$repo=Split-Path -Parent $root
Set-Location $repo
if (!(Test-Path '.\ugi\engine.py')) {throw 'Extract this package inside UGI event repo (beside ugi and compose.yaml)'}
if (!(Get-Command docker -ErrorAction SilentlyContinue)) {throw 'Docker Desktop CLI missing'}
$cid=(docker compose ps -q api | Select-Object -First 1)
if (!$cid) {throw 'UGI api container not running: docker compose up -d graph api'}
$cid=$cid.Trim()
# NEVER certify stale Docker code while uncommitted H1 files differ on host.
# This is read-only. It refuses to auto-rebuild or overwrite a running image.
foreach ($name in @('engine.py','mcp_server.py','models.py','store.py','extract.py','api.py')) {
    $hostFile=Join-Path $repo ('ugi\'+$name)
    if (!(Test-Path $hostFile)) {throw "UGI host file missing: $name"}
    $hostHash=(Get-FileHash -Algorithm SHA256 $hostFile).Hash.ToLowerInvariant()
    $remoteHash=(& docker exec $cid sha256sum "/app/ugi/$name")
    if ($LASTEXITCODE -ne 0) {throw "Cannot check running API source: $name"}
    $remoteHex=($remoteHash -split '\s+')[0].ToLowerInvariant()
    if ($hostHash -ne $remoteHex) {
        throw "RUNNING API DOES NOT MATCH HOST UGI/$name. Do not certify stale code. Rebuild api deliberately when safe, then rerun."
    }
}
Write-Host 'Host source matches running API container for 6 critical files.' -ForegroundColor Green
# Source hash is an audit guard; neither repo, volumes nor H1 files are changed.
$before=(Get-ChildItem -LiteralPath (Join-Path $repo 'ugi') -Filter *.py -Recurse -File |
  Sort-Object FullName | ForEach-Object { "$_=$((Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash)" }) -join "`n"
$runId=[guid]::NewGuid().ToString('N').Substring(0,12)
$pkg="/tmp/ugi_final_pkg_$runId"
$engineDir="/tmp/ugi_final_engine_$runId"
$reportsDir=Join-Path $root "results\$runId"
New-Item -ItemType Directory -Force $reportsDir | Out-Null
Write-Host "`n=== UGI FINAL QUALIFICATION RUN $runId ===" -ForegroundColor Cyan
Write-Host 'Creating unique container dirs. No old files removed, no graph namespace reused.' -ForegroundColor Yellow
& docker cp "$root\." "${cid}:$pkg"
if ($LASTEXITCODE -ne 0) {throw 'docker cp of qualification package failed'}
$common="${pkg}:${pkg}/aio:/app"
$offlineOK=$true
$unitJobs=@(
   @('P5 memory / concurrency','p5tests','test_*.py'),
   @('Guided Rulebook','aio/ugi_rulebook/tests','test_*.py'),
   @('Real-source manifest parser','aio/ugi_real_track1/tests','test_*.py'),
   @('Read-only logic','aio/ugi_krish_validation_v2/tests','test_*.py'),
   @('Previous guarded patch regressions','aio/ugi_agent_fix/tests','test_patch_and_agent.py'),
   @('Previous orchestration regressions','aio/ugi_agent_fix/tests','test_orchestrator.py'),
   @('Combined MCP-to-receipt regressions','tests','test_*.py')
)
foreach ($j in $unitJobs) {
    Write-Host "`n=== UNIT: $($j[0]) ===" -ForegroundColor Cyan
    & docker exec -e "PYTHONPATH=$common" -w $pkg $cid python -m unittest discover -s "$pkg/$($j[1])" -p $j[2] -v
    if ($LASTEXITCODE -ne 0) {$offlineOK=$false;Write-Warning "FAILED: $($j[0])"}
}
Write-Host "`n=== TESTING EPHEMERAL ENGINE PATCH ===" -ForegroundColor Cyan
& docker exec $cid sh -c "mkdir -p $engineDir && cp -R /app/ugi $engineDir/ugi"
if ($LASTEXITCODE -ne 0) {throw 'Cannot prepare disposable engine copy'}
$patchRc="/tmp/ugi_final_patch_$runId.json"
& docker exec -e "PYTHONPATH=$common" -w $pkg $cid python -m ugi_agent_fix.patch_engine --input /app/ugi/engine.py --output "$engineDir/ugi/engine.py" --receipt $patchRc
$patchOK=($LASTEXITCODE -eq 0)
$pyPath="${engineDir}:${common}"
if ($patchOK) {
    & docker exec -e "PYTHONPATH=$pyPath" -w $pkg $cid python -m unittest discover -s "$pkg/aio/ugi_agent_fix/tests" -p test_engine_patch.py -v
    if ($LASTEXITCODE -ne 0) {$patchOK=$false}
}
if (!$patchOK) {throw 'Ephemeral patch incompatible. Original UGI untouched. Abort live experiment.'}
& docker exec -e "PYTHONPATH=$pyPath" -w "$pkg/aio" $cid python -m ugi_rulebook.preflight --expected-root "$pkg/aio" --expected-engine "$engineDir/ugi/engine.py"
if ($LASTEXITCODE -ne 0) {throw 'Python module path origin mismatch, fail closed'}
$appTestStatus='NOT_RUN'
if ($IncludeNativeUGITests) {
    Write-Host "`n=== NATIVE UGI MEMORY-BACKEND TESTS (OPTIONAL) ===" -ForegroundColor Cyan
    & docker exec -e "PYTHONPATH=$pyPath" -e 'UGI_BACKEND=memory' -e 'UGI_PROVIDER=offline' -e 'UGI_ALLOW_PAID_CALLS=false' -w /app $cid python -m pytest -q /app/tests/test_mcp.py /app/tests/test_regressions.py
    $appTestStatus=if ($LASTEXITCODE -eq 0) {'PASS'} else {'FAIL'}
}
$p5out="/tmp/ugi_final_p5_$runId.json"
$v5out="/tmp/ugi_final_v5_$runId.json"
$comboout="/tmp/ugi_final_combo_$runId.json"
$decisionout="/tmp/ugi_final_decision_$runId.json"
Write-Host "`n=== P5 FULL SYNTHETIC (17 SCENARIOS) ===" -ForegroundColor Cyan
& docker exec -e "PYTHONPATH=$pyPath" -w $pkg $cid python -m p5memory.run_lab --report $p5out
$p5Exit=$LASTEXITCODE
Write-Host "`n=== EXISTING 49 LIVE MCP WORKFLOWS ===" -ForegroundColor Cyan
$v5Args=@('exec','-e',"PYTHONPATH=$pyPath",'-e','UGI_REDIS_URL=redis://graph:6379/0','-w',"$pkg/aio",$cid,'python','-m','ugi_rulebook.experiment','--output',$v5out,'--model',$OllamaModel,'--ollama-url',$OllamaUrl)
if ($SkipLLM) {$v5Args+='--no-advisor'} else {$v5Args+='--run-legacy-agent'}
& docker @v5Args
$v5Exit=$LASTEXITCODE
Write-Host "`n=== NEW: REAL FALKORDB + MCP + P5 RECEIPTS COMBINED ===" -ForegroundColor Cyan
& docker exec -e "PYTHONPATH=$pyPath" -e 'UGI_REDIS_URL=redis://graph:6379/0' -w $pkg $cid python -m ugi_final.live_combo --output $comboout
$comboExit=$LASTEXITCODE
Write-Host "`n=== EXPORTING ALL REPORTS ===" -ForegroundColor Cyan
$inputMap=@{'rulebook_result.json'=$v5out;'p5_lab_report.json'=$p5out;'combined_graph_memory.json'=$comboout;'patch_receipt.json'=$patchRc}
foreach ($fname in $inputMap.Keys) {
    & docker cp "${cid}:$($inputMap[$fname])" (Join-Path $reportsDir $fname)
    if ($LASTEXITCODE -ne 0) {Write-Warning "MISSING REPORT: $fname"}
}
$unitFlag=if ($offlineOK) {'1'} else {'0'}
$patchFlag=if ($patchOK) {'1'} else {'0'}
& docker exec -e "PYTHONPATH=$pyPath" -w $pkg $cid python -m ugi_final.report_builder --v5 $v5out --p5 $p5out --combined $comboout --out $decisionout --unit-ok $unitFlag --patch-ok $patchFlag --app-tests $appTestStatus
$decisionExit=$LASTEXITCODE
& docker cp "${cid}:$decisionout" (Join-Path $reportsDir 'FINAL_DECISION.json')
if ($LASTEXITCODE -ne 0) {throw 'Final decision report export failed'}
$after=(Get-ChildItem -LiteralPath (Join-Path $repo 'ugi') -Filter *.py -Recurse -File |
  Sort-Object FullName | ForEach-Object { "$_=$((Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash)" }) -join "`n"
if ($before -ne $after) {throw 'UGI source hashes changed during experiment! Stop.'}
Write-Host "`n=== FINAL QUALIFICATION RESULTS ===" -ForegroundColor Cyan
Write-Host "All reports: $reportsDir" -ForegroundColor Green
Write-Host "Original UGI Python source SHA-256 list unchanged." -ForegroundColor Green
if ($v5Exit -ne 0 -or $p5Exit -ne 0 -or $comboExit -ne 0 -or $decisionExit -ne 0 -or !$offlineOK) {
    Write-Warning 'Some checks failed. Do not integrate yet. Upload FINAL_DECISION.json and reports.'
    exit 1
}
Write-Host 'Qualification suite passed under defined scope. NOT production-ready and NOT deployed.' -ForegroundColor Green
