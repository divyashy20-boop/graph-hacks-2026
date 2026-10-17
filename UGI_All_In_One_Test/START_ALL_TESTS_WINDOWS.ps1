param(
    [string]$OllamaModel = 'qwen3:4b-instruct',
    [string]$OllamaUrl = 'http://host.docker.internal:11434',
    [switch]$SkipLLM,
    [switch]$RunLegacyAgent
)
$ErrorActionPreference='Stop'
$root=$PSScriptRoot
$sourcePath=Join-Path (Split-Path -Parent $root) 'ugi\engine.py'
$sourceBefore=if (Test-Path $sourcePath) {(Get-FileHash -Algorithm SHA256 $sourcePath).Hash} else {''}
$repo=Split-Path -Parent $root
Set-Location $repo
if (!(Test-Path (Join-Path $repo 'ugi\engine.py'))) { throw 'Extract ZIP inside existing UGI event folder alongside ugi and compose.yaml' }
if (!(Get-Command docker -ErrorAction SilentlyContinue)) { throw 'Docker CLI unavailable' }
$cid=(docker compose ps -q api | Select-Object -First 1)
if (!$cid) { throw 'UGI API container not running. Start Docker Desktop and run docker compose up -d graph api' }
$cid=$cid.Trim()

Write-Host "`n=== 1/5 COPYING ISOLATED RULEBOOK PACKAGE ===" -ForegroundColor Cyan
# Docker cp can leave root-owned files after earlier runs. Never delete or chmod
# any previous temp directory. A new UUID path is safer and avoids stale imports.
$runId=[guid]::NewGuid().ToString('N').Substring(0,12)
$testCwd="/tmp/ugi_aio_pkg_${runId}"
$hotfixDir="/tmp/ugi_aio_engine_${runId}"
$liveReport="/tmp/ugi_aio_result_${runId}.json"
$patchReceipt="/tmp/ugi_aio_patch_${runId}.json"
Write-Host "Isolated run ID: $runId" -ForegroundColor Yellow
& docker cp "$root\." "${cid}:$testCwd"
if ($LASTEXITCODE -ne 0) {throw 'Failed to copy isolated testing package'}
& docker exec $cid test -f "$testCwd/VERSION.txt"
if ($LASTEXITCODE -ne 0) {throw 'Copied testing package missing VERSION.txt'}
$common="${testCwd}:/tmp/ugi_mcp_sdk:/app" 

Write-Host "`n=== 2/5 OFFLINE UNIT / PARSER / SECURITY TESTS ===" -ForegroundColor Cyan
$testDirs=@('ugi_rulebook/tests','ugi_real_track1/tests','ugi_krish_validation_v2/tests')
foreach ($folder in $testDirs) {
    docker exec -e "PYTHONPATH=$common" -w $testCwd $cid python -m unittest discover -s "$testCwd/$folder" -v
    if ($LASTEXITCODE -ne 0) {throw "Offline tests failed in $folder. Production files untouched."}
}
foreach ($test in @('test_patch_and_agent.py','test_orchestrator.py')) {
    docker exec -e "PYTHONPATH=$common" -w $testCwd $cid python -m unittest discover -s "$testCwd/ugi_agent_fix/tests" -p $test -v
    if ($LASTEXITCODE -ne 0) { throw "Regression failed: $test" }
}

# Verify this is the repaired release, not cached v1 files.
docker exec -e "PYTHONPATH=$common" -w $testCwd $cid python -c "from ugi_agent_fix.patch_engine import PATCH_VERSION; assert PATCH_VERSION == 'ugi-rule-resolution-consistency-v2', PATCH_VERSION; print('Guarded patcher version:', PATCH_VERSION)"
if ($LASTEXITCODE -ne 0) { throw 'Wrong/old patcher copied into container. Re-extract latest all-in-one ZIP.' }

Write-Host "`n=== 3/5 PATCHING AN EPHEMERAL COPY OF UGI ENGINE ===" -ForegroundColor Cyan
# Separate from previous H1 workspace and earlier /tmp/ugi_hotfix experiments.
docker exec $cid sh -c "mkdir -p $hotfixDir && cp -R /app/ugi $hotfixDir/ugi"
if ($LASTEXITCODE -ne 0) {throw 'Could not prepare app copy'}
docker exec -e "PYTHONPATH=$common" -w $testCwd $cid python -m ugi_agent_fix.patch_engine --input /app/ugi/engine.py --output "$hotfixDir/ugi/engine.py" --receipt $patchReceipt
if ($LASTEXITCODE -ne 0) {throw 'Engine version incompatible with previous safe explanation patch; no original source modified'}
$patched="${hotfixDir}:${common}"
docker exec -e "PYTHONPATH=$patched" -w $testCwd $cid python -m unittest discover -s "$testCwd/ugi_agent_fix/tests" -p test_engine_patch.py -v
if ($LASTEXITCODE -ne 0) {throw 'Patched-copy engine tests failed; original UGI unchanged'}

Write-Host "`n=== RUNTIME IMPORT ORIGIN CHECK (NO STALE /tmp MODULES) ===" -ForegroundColor Cyan
docker exec -e "PYTHONPATH=$patched" -w $testCwd $cid python -m ugi_rulebook.preflight --expected-root $testCwd --expected-engine "$hotfixDir/ugi/engine.py"
if ($LASTEXITCODE -ne 0) {throw 'Wrong Python package imported (stale /tmp files). Live graph test cancelled safely.'}

Write-Host "`n=== 4/5 REAL FALKORDB + MCP + OPTIONAL QWEN EXPERIMENT ===" -ForegroundColor Cyan
# Unique report path per run. No deletions or writes to previous reports.
$argv=@('exec','-e',"PYTHONPATH=$patched",'-e','UGI_REDIS_URL=redis://graph:6379/0','-w',$testCwd,$cid,'python','-m','ugi_rulebook.experiment', '--output',$liveReport,'--model',$OllamaModel,'--ollama-url',$OllamaUrl)
if ($SkipLLM) {$argv+= '--no-advisor'}
if ($RunLegacyAgent) {$argv+= '--run-legacy-agent'}
& docker @argv
$liveExit=$LASTEXITCODE

Write-Host "`n=== 5/5 COPY AUDIT AND SOURCE PATCH RECEIPT ===" -ForegroundColor Cyan
$reports=Join-Path $root 'results'
New-Item -ItemType Directory -Force $reports | Out-Null
# Preserve earlier audit results before replacing latest report names.
$previous=Join-Path $reports 'rulebook_result.json'
$priorReceipt=Join-Path $reports 'patch_receipt.json'
if ((Test-Path $previous) -or (Test-Path $priorReceipt)) {
    $archive=Join-Path $reports ('history_' + (Get-Date -Format 'yyyyMMdd_HHmmss') + '_' + [guid]::NewGuid().ToString('N').Substring(0,6))
    New-Item -ItemType Directory -Force $archive | Out-Null
    foreach ($saved in @($previous,$priorReceipt)) {
        if (Test-Path $saved) { Copy-Item -LiteralPath $saved -Destination $archive }
    }
    Write-Host "Previous audit report saved in: $archive" -ForegroundColor Yellow
}
docker cp "${cid}:$liveReport" (Join-Path $reports 'rulebook_result.json')
if ($LASTEXITCODE -ne 0) { throw 'Live report absent; see Docker traceback above' }
docker cp "${cid}:$patchReceipt" (Join-Path $reports 'patch_receipt.json')
if ($LASTEXITCODE -ne 0) { throw 'Patch receipt missing' }
# Persist the correct isolated locations for RUN_ONE_QUERY_WINDOWS.ps1.
# Write this only AFTER a valid live report and receipt were copied.
$runtime=[ordered]@{
    run_id=$runId
    container_id=$cid
    package_dir=$testCwd
    hotfix_dir=$hotfixDir
    pythonpath=$patched
    live_report=$liveReport
    patch_receipt=$patchReceipt
    recorded_utc=(Get-Date).ToUniversalTime().ToString('o')
}
$runtimeFile=Join-Path $reports 'runtime_paths.json'
if (Test-Path $runtimeFile) {
    $oldRuntime=Join-Path $reports ('runtime_paths_previous_' + (Get-Date -Format 'yyyyMMdd_HHmmss') + '_' + [guid]::NewGuid().ToString('N').Substring(0,6) + '.json')
    Copy-Item -LiteralPath $runtimeFile -Destination $oldRuntime
}
$runtime | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 -LiteralPath $runtimeFile
$r=Get-Content (Join-Path $reports 'rulebook_result.json') -Raw | ConvertFrom-Json
$wf=@($r.workflows)
$good=@($wf | Where-Object {$_.benchmark_pass -eq $true}).Count
Write-Host "`n====== FINAL TEST RESULT ======" -ForegroundColor Cyan
Write-Host "Guided rulebook COMPLETE & correct: $good / $($wf.Count)"
$extended=@($r.extended_workflows)
$extendedOK=@($extended | Where-Object {$_.passed -eq $true}).Count
Write-Host "Extended live MCP cases: $extendedOK / $($extended.Count)"
Write-Host "Ollama advisor available: $($r.ai_advisor_available)"
Write-Host "Report saved: $(Join-Path $reports 'rulebook_result.json')" -ForegroundColor Green
Write-Host "Runtime paths saved: $runtimeFile" -ForegroundColor Green
$sourceAfter=(Get-FileHash -Algorithm SHA256 $sourcePath).Hash
if ($sourceAfter -ne $sourceBefore) {throw 'Host UGI engine hash changed during run! Do not continue.'}
Write-Host 'Host ugi/engine.py SHA256 unchanged; original database namespaces not intentionally modified.' -ForegroundColor Yellow
if ($liveExit -ne 0) { Write-Warning 'Live test failed. Upload rulebook_result.json and PowerShell output.'; exit 1 }
Write-Host 'Bounded guided-workflow test completed. General autonomous-agent performance is not proven.' -ForegroundColor Green
