param(
    [Parameter(Mandatory=$true)][ValidateSet('nginx-flask-mysql','nginx-nodejs-redis','nginx-flask-mongo','flask-redis','nginx-golang-postgres')][string]$Dataset,
    [Parameter(Mandatory=$true)][string]$Query
)
$ErrorActionPreference='Stop'
$root=$PSScriptRoot
$repo=Split-Path -Parent $root
Set-Location $repo
$report=Join-Path $root 'results\rulebook_result.json'
if (!(Test-Path $report)) {throw 'Run START_ALL_TESTS_WINDOWS.ps1 first; isolated graph report missing'}
$cid=(docker compose ps -q api | Select-Object -First 1)
if (!$cid) {throw 'Docker API container not running'}
$cid=$cid.Trim()
$runtimeFile=Join-Path $root 'results\runtime_paths.json'
if (!(Test-Path $runtimeFile)) {throw 'Run START_ALL_TESTS_WINDOWS.ps1 v5 first; runtime paths missing'}
$runtime=Get-Content -LiteralPath $runtimeFile -Raw | ConvertFrom-Json
# Refuse stale metadata after container restart or malformed/foreign paths.
if ($runtime.container_id -ne $cid) {throw 'Docker API container changed since test. Rerun START_ALL_TESTS_WINDOWS.ps1.'}
if ($runtime.package_dir -notmatch '^/tmp/ugi_aio_pkg_[0-9a-f]{12}$') {throw 'Untrusted package path in runtime metadata'}
if ($runtime.hotfix_dir -notmatch '^/tmp/ugi_aio_engine_[0-9a-f]{12}$') {throw 'Untrusted hotfix path in runtime metadata'}
if ($runtime.live_report -notmatch '^/tmp/ugi_aio_result_[0-9a-f]{12}\.json$') {throw 'Untrusted report path in runtime metadata'}
$expectedPath="$($runtime.hotfix_dir):$($runtime.package_dir):/tmp/ugi_mcp_sdk:/app"
if ($runtime.pythonpath -ne $expectedPath) {throw 'Untrusted Python import path in runtime metadata'}
& docker exec $cid test -f "$($runtime.package_dir)/VERSION.txt"
if ($LASTEXITCODE -ne 0) {throw 'Isolated test package absent in Docker. Rerun START_ALL_TESTS_WINDOWS.ps1.'}
$guid=[guid]::NewGuid().ToString('N').Substring(0,12)
$temp="/tmp/ugi_v3_one_query_$guid.json"
$local=Join-Path (Join-Path $root 'results') "single_query_$guid.json"
# Passing the text as Docker CLI argv; avoid shell interpolation of user query.
& docker exec -e "PYTHONPATH=$expectedPath" -e 'UGI_REDIS_URL=redis://graph:6379/0' -w $runtime.package_dir $cid python -m ugi_rulebook.query_against_test_graph --report $runtime.live_report --dataset $Dataset --query $Query --output $temp
$ec=$LASTEXITCODE
& docker cp "${cid}:$temp" $local
if ($LASTEXITCODE -ne 0) {throw 'Single-query report was not created'}
Write-Host "Report: $local" -ForegroundColor Green
if ($ec -ne 0) {Write-Warning 'Request abstained or failed; review report JSON.'}
