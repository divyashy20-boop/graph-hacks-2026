# Final qualification surgical retest: only P5 safety, bridge regressions,
# actual UGI engine consistency and 11 live FalkorDB+MCP+P5 cases.
# Does not modify original host UGI files, H1, graph volumes or current graph
# namespaces. It creates NEW disposable graph namespaces for live scenarios.
$ErrorActionPreference='Stop'
$root=$PSScriptRoot
$repo=Split-Path -Parent $root
Set-Location $repo
if (!(Test-Path '.\ugi\engine.py')) {throw 'Extract beside ugi/ and compose.yaml in the UGI event repo'}
if (!(Get-Command docker -ErrorAction SilentlyContinue)) {throw 'Docker Desktop CLI missing'}
$cid=(docker compose ps -q api | Select-Object -First 1)
if (!$cid) {throw 'UGI API container not running'}
$cid=$cid.Trim()
# Do not silently validate stale Docker image over uncommitted H1 changes.
foreach ($name in @('engine.py','mcp_server.py','models.py','store.py','extract.py','api.py')) {
    $hostFile=Join-Path $repo ('ugi\'+$name)
    if (!(Test-Path $hostFile)) {throw "Missing host source: $name"}
    $h=(Get-FileHash -Algorithm SHA256 -LiteralPath $hostFile).Hash.ToLowerInvariant()
    $rem=(& docker exec $cid sha256sum "/app/ugi/$name")
    if ($LASTEXITCODE -ne 0) {throw "Docker hash check failed: $name"}
    $r=($rem -split '\s+')[0].ToLowerInvariant()
    if ($h -ne $r) {throw "Running API differs from host UGI/$name; do not test stale H1 code"}
}
$before=@{}
foreach ($f in (Get-ChildItem -LiteralPath (Join-Path $repo 'ugi') -Recurse -File -Filter '*.py')) {
    $before[$f.FullName]=(Get-FileHash -LiteralPath $f.FullName -Algorithm SHA256).Hash
}
$runId=[guid]::NewGuid().ToString('N').Substring(0,12)
$pkg="/tmp/ugi_p5_fix_pkg_$runId"
$patchDir="/tmp/ugi_p5_fix_engine_$runId"
$reports=Join-Path $root "results\p5_fix_$runId"
New-Item -ItemType Directory -Force $reports | Out-Null
Write-Host "`n=== UGI P5 SURGICAL LIVE RETEST: $runId ===" -ForegroundColor Cyan
Write-Host 'Fresh disposable directories. No old containers, source or graph volumes deleted.'
& docker cp "$root\." "${cid}:$pkg"
if ($LASTEXITCODE -ne 0) {throw 'Docker cp failed'}
$imports="${pkg}:${pkg}/aio:/app"
$unitsOK=$true
foreach ($job in @(@('P5 memory / concurrency','p5tests'),@('UGI MCP / P5 integration / surgical regressions','tests'))) {
    Write-Host "`n=== $($job[0]) ===" -ForegroundColor Cyan
    & docker exec -e "PYTHONPATH=$imports" -w $pkg $cid python -m unittest discover -s "$pkg/$($job[1])" -p 'test_*.py' -v
    if ($LASTEXITCODE -ne 0) {$unitsOK=$false; Write-Warning "Test suite failed: $($job[0])"}
}
# Real integration uses the verified explanation-consistency hotfix ONLY in a
# disposable engine copy. Never overwrite /app/ugi/engine.py.
& docker exec $cid sh -c "mkdir -p $patchDir && cp -R /app/ugi $patchDir/ugi"
if ($LASTEXITCODE -ne 0) {throw 'Cannot prepare isolated engine copy'}
$patchReceipt="/tmp/ugi_p5_fix_patch_$runId.json"
& docker exec -e "PYTHONPATH=$imports" -w $pkg $cid python -m ugi_agent_fix.patch_engine --input /app/ugi/engine.py --output "$patchDir/ugi/engine.py" --receipt $patchReceipt
if ($LASTEXITCODE -ne 0) {throw 'Engine hotfix not compatible; original UGI unchanged'}
$runtime="${patchDir}:${imports}"
& docker exec -e "PYTHONPATH=$runtime" -w "$pkg/aio" $cid python -m ugi_rulebook.preflight --expected-root "$pkg/aio" --expected-engine "$patchDir/ugi/engine.py"
if ($LASTEXITCODE -ne 0) {throw 'Refusing stale /tmp Python import'}
Write-Host "`n=== REAL FALKORDB + MCP + P5 (11 live cases) ===" -ForegroundColor Cyan
$combo="/tmp/ugi_p5_fix_combo_$runId.json"
& docker exec -e "PYTHONPATH=$runtime" -e 'UGI_REDIS_URL=redis://graph:6379/0' -w $pkg $cid python -m ugi_final.live_combo --output $combo
$comboExit=$LASTEXITCODE
& docker cp "${cid}:$combo" (Join-Path $reports 'combined_graph_memory.json')
if ($LASTEXITCODE -ne 0) {throw 'Combined report missing; cannot qualify'}
& docker cp "${cid}:$patchReceipt" (Join-Path $reports 'patch_receipt.json')
if ($LASTEXITCODE -ne 0) {throw 'Patch receipt missing; cannot qualify'}
$unitFlag=if ($unitsOK) {'PASS'} else {'FAIL'}
$liveFlag=if ($comboExit -eq 0) {'PASS'} else {'FAIL'}
$reportTemp="/tmp/ugi_p5_fix_decision_$runId.json"
& docker exec -e "PYTHONPATH=$runtime" -w $pkg $cid python -m ugi_final.focused_report --combo $combo --units $unitFlag --live $liveFlag --output $reportTemp
$decisionExit=$LASTEXITCODE
& docker cp "${cid}:$reportTemp" (Join-Path $reports 'P5_FIX_DECISION.json')
if ($LASTEXITCODE -ne 0) {throw 'Decision report missing; cannot qualify'}
foreach ($f in (Get-ChildItem -LiteralPath (Join-Path $repo 'ugi') -Recurse -File -Filter '*.py')) {
    if (!$before.ContainsKey($f.FullName)) {throw 'Host UGI file list changed'}
    $now=(Get-FileHash -LiteralPath $f.FullName -Algorithm SHA256).Hash
    if ($before[$f.FullName] -ne $now) {throw "Original UGI host file changed: $($f.FullName)"}
}
Write-Host "`nReports: $reports" -ForegroundColor Yellow
if (!$unitsOK -or $comboExit -ne 0 -or $decisionExit -ne 0) {
    Write-Warning 'P5 FIX NOT QUALIFIED. Do not integrate P5 until failures fixed.'
    exit 1
}
Write-Host 'P5 FIX QUALIFIED FOR FEATURE-FLAGGED INTEGRATION TESTING (NOT PRODUCTION).' -ForegroundColor Green
