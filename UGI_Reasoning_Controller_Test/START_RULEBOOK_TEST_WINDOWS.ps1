param(
    [string]$OllamaModel = 'qwen3:4b-instruct',
    [string]$OllamaUrl = 'http://host.docker.internal:11434',
    [switch]$SkipLLM,
    [switch]$RunLegacyAgent
)
$ErrorActionPreference='Stop'
$root=$PSScriptRoot
$repo=Split-Path -Parent $root
Set-Location $repo
if (!(Test-Path (Join-Path $repo 'ugi\engine.py'))) { throw 'Extract ZIP inside existing UGI event folder alongside ugi and compose.yaml' }
if (!(Get-Command docker -ErrorAction SilentlyContinue)) { throw 'Docker CLI unavailable' }
$cid=(docker compose ps -q api | Select-Object -First 1)
if (!$cid) { throw 'UGI API container not running. Start Docker Desktop and run docker compose up -d graph api' }
$cid=$cid.Trim()

Write-Host "`n=== 1/5 COPYING ISOLATED RULEBOOK PACKAGE ===" -ForegroundColor Cyan
docker cp "$root\." "${cid}:/tmp/ugi_rulebook_pkg"
if ($LASTEXITCODE -ne 0) {throw 'Copy failed'}
$common='/tmp/ugi_rulebook_pkg:/tmp/ugi_mcp_sdk:/tmp:/app'

Write-Host "`n=== 2/5 OFFLINE UNIT / PARSER / SECURITY TESTS ===" -ForegroundColor Cyan
$testDirs=@('ugi_rulebook/tests','ugi_real_track1/tests','ugi_krish_validation_v2/tests')
foreach ($folder in $testDirs) {
    docker exec -e "PYTHONPATH=$common" -w /tmp $cid python -m unittest discover -s "/tmp/ugi_rulebook_pkg/$folder" -v
    if ($LASTEXITCODE -ne 0) {throw "Offline tests failed in $folder. Production files untouched."}
}
foreach ($test in @('test_patch_and_agent.py','test_orchestrator.py')) {
    docker exec -e "PYTHONPATH=$common" -w /tmp $cid python -m unittest discover -s /tmp/ugi_rulebook_pkg/ugi_agent_fix/tests -p $test -v
    if ($LASTEXITCODE -ne 0) { throw "Regression failed: $test" }
}

# Verify this is the repaired release, not cached v1 files.
docker exec -e "PYTHONPATH=$common" -w /tmp $cid python -c "from ugi_agent_fix.patch_engine import PATCH_VERSION; assert PATCH_VERSION == 'ugi-rule-resolution-consistency-v2', PATCH_VERSION; print('Guarded patcher version:', PATCH_VERSION)"
if ($LASTEXITCODE -ne 0) { throw 'Wrong/old patcher copied into container. Re-extract corrected v2 ZIP.' }

Write-Host "`n=== 3/5 PATCHING AN EPHEMERAL COPY OF UGI ENGINE ===" -ForegroundColor Cyan
# Separate from previous H1 workspace and earlier /tmp/ugi_hotfix experiments.
docker exec $cid sh -c 'mkdir -p /tmp/ugi_rulebook_hotfix && cp -R /app/ugi /tmp/ugi_rulebook_hotfix/ugi'
if ($LASTEXITCODE -ne 0) {throw 'Could not prepare app copy'}
docker exec -e "PYTHONPATH=$common" -w /tmp $cid python -m ugi_agent_fix.patch_engine --input /app/ugi/engine.py --output /tmp/ugi_rulebook_hotfix/ugi/engine.py --receipt /tmp/ugi_rulebook_patch_receipt.json
if ($LASTEXITCODE -ne 0) {throw 'Engine version incompatible with previous safe explanation patch; no original source modified'}
$patched="/tmp/ugi_rulebook_hotfix:$common"
docker exec -e "PYTHONPATH=$patched" -w /tmp $cid python -m unittest discover -s /tmp/ugi_rulebook_pkg/ugi_agent_fix/tests -p test_engine_patch.py -v
if ($LASTEXITCODE -ne 0) {throw 'Patched-copy engine tests failed; original UGI unchanged'}

Write-Host "`n=== 4/5 REAL FALKORDB + MCP + OPTIONAL QWEN EXPERIMENT ===" -ForegroundColor Cyan
$argv=@('exec','-e',"PYTHONPATH=$patched",'-e','UGI_REDIS_URL=redis://graph:6379/0','-w','/tmp',$cid,'python','-m','ugi_rulebook.experiment', '--output','/tmp/ugi_rulebook_result.json','--model',$OllamaModel,'--ollama-url',$OllamaUrl)
if ($SkipLLM) {$argv+= '--no-advisor'}
if ($RunLegacyAgent) {$argv+= '--run-legacy-agent'}
& docker @argv
$liveExit=$LASTEXITCODE

Write-Host "`n=== 5/5 COPY AUDIT AND SOURCE PATCH RECEIPT ===" -ForegroundColor Cyan
$reports=Join-Path $root 'results'
New-Item -ItemType Directory -Force $reports | Out-Null
docker cp "${cid}:/tmp/ugi_rulebook_result.json" (Join-Path $reports 'rulebook_result.json')
if ($LASTEXITCODE -ne 0) { throw 'Live report absent; see Docker traceback above' }
docker cp "${cid}:/tmp/ugi_rulebook_patch_receipt.json" (Join-Path $reports 'patch_receipt.json')
if ($LASTEXITCODE -ne 0) { throw 'Patch receipt missing' }
$r=Get-Content (Join-Path $reports 'rulebook_result.json') -Raw | ConvertFrom-Json
$wf=@($r.workflows)
$good=@($wf | Where-Object {$_.benchmark_pass -eq $true}).Count
Write-Host "`n====== FINAL TEST RESULT ======" -ForegroundColor Cyan
Write-Host "Guided rulebook COMPLETE & correct: $good / $($wf.Count)"
Write-Host "Ollama advisor available: $($r.ai_advisor_available)"
Write-Host "Report saved: $(Join-Path $reports 'rulebook_result.json')" -ForegroundColor Green
Write-Host 'Existing UGI code and databases were not overwritten. Test graphs are new, isolated names.' -ForegroundColor Yellow
if ($liveExit -ne 0) { Write-Warning 'Live test failed. Upload rulebook_result.json and PowerShell output.'; exit 1 }
Write-Host 'Bounded guided-workflow test completed. General autonomous-agent performance is not proven.' -ForegroundColor Green
