$ErrorActionPreference = 'Stop'
$lab = Split-Path -Parent $MyInvocation.MyCommand.Path
$repo = Split-Path -Parent $lab
Set-Location $repo
$cid = docker compose ps -q api 2>$null | Select-Object -First 1
if (-not $cid) { throw 'UGI API container missing. Start your existing compose stack first: docker compose up -d' }
$runID = [guid]::NewGuid().ToString('N').Substring(0,12)
$containerDir = '/tmp/ugi_p5_pkg_' + $runID
$remoteReport = '/tmp/ugi_p5_report_' + $runID + '.json'
$resultsDir = Join-Path $lab 'results'
New-Item -ItemType Directory -Path $resultsDir -Force | Out-Null
$hostEngine = Join-Path $repo 'ugi\engine.py'
$engineBefore = if (Test-Path $hostEngine) { (Get-FileHash -Algorithm SHA256 $hostEngine).Hash } else { '' }
Write-Host "=== UGI P5 MEMORY LAB: isolated run $runID ==="
Write-Host 'Original UGI, Git and graph volumes will not be modified.'
& docker cp $lab "${cid}:$containerDir"
if ($LASTEXITCODE -ne 0) {throw 'Docker package copy failed'}
Write-Host '=== 1/3 RUN UNIT + SAFETY + CONCURRENCY TESTS ==='
& docker exec -w $containerDir $cid python -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) {throw 'P5 offline suite failed; no success claimed'}
Write-Host '=== 2/3 RUN 17 LIVE LOCAL-SQLITE SCENARIOS ==='
& docker exec -w $containerDir $cid python -m p5memory.run_lab --report $remoteReport
if ($LASTEXITCODE -ne 0) {throw 'P5 scenario evaluation failed'}
Write-Host '=== 3/3 EXPORT REPORT AND VERIFY ORIGINAL ENGINE HASH ==='
$destination = Join-Path $resultsDir ('p5_lab_report_' + $runID + '.json')
& docker cp "${cid}:$remoteReport" $destination
if ($LASTEXITCODE -ne 0) {throw 'Failed to export report'}
Copy-Item -LiteralPath $destination -Destination (Join-Path $resultsDir 'p5_lab_report_latest.json') -Force
$engineAfter = if (Test-Path $hostEngine) { (Get-FileHash -Algorithm SHA256 $hostEngine).Hash } else { '' }
if ($engineBefore -ne $engineAfter) {throw 'Original engine.py hash changed unexpectedly! Investigate before proceeding.'}
$report = Get-Content -Raw -LiteralPath $destination | ConvertFrom-Json
if ($report.fail -ne 0 -or $report.pass -ne $report.total) {throw 'P5 report has failed scenarios'}
Write-Host "ALL P5 TESTS PASSED. Benchmarks: $($report.pass)/$($report.total)" -ForegroundColor Green
Write-Host "Detailed report: $destination"
Write-Host 'Important: synthetic SQLite P5 proof only. Real FalkorDB integration / external-action atomicity NOT demonstrated.'
