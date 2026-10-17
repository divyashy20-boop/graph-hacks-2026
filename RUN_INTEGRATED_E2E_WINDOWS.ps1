# Safe real API -> FalkorDB -> MCP -> receipt -> freshness E2E.
# Only uses a NEW disposable dataset, never deletes any existing graph/volume.
param([string]$BaseUrl = 'http://127.0.0.1:8001')
$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $MyInvocation.MyCommand.Path
$run = [guid]::NewGuid().ToString('N').Substring(0,12)
$dataset = 'ugibeta_' + $run
$out = Join-Path $repo ('integration-results\e2e_' + $run)
New-Item -ItemType Directory -Force -Path $out | Out-Null
$h = @{'X-Dataset'=$dataset}
if ($env:UGI_DEMO_API_KEY) { $h['X-API-Key'] = $env:UGI_DEMO_API_KEY }
$report = [ordered]@{version='ugi-guided-p5-http-e2e-v1'; run_id=$run; dataset=$dataset; result='NOT_RUN'; checks=@(); external_actions_enabled=$false; graph_deleted=$false}
function Check([string]$label, [bool]$ok, $details) {
  $script:report.checks += @{name=$label; pass=$ok; detail=$details}
  if (-not $ok) { throw ('E2E FAIL: ' + $label + ' - ' + ($details | ConvertTo-Json -Compress -Depth 5)) }
  Write-Host ('PASS ' + $label)
}
function JsonBody($v) { return (ConvertTo-Json -InputObject $v -Depth 8 -Compress) }
function PostJson([string]$path, $data) {
  return Invoke-RestMethod -Method Post -Uri ($BaseUrl + $path) -Headers $h -ContentType 'application/json' -Body (JsonBody $data)
}
function GetJson([string]$path) { return Invoke-RestMethod -Uri ($BaseUrl + $path) -Headers $h }
function UploadEdge([string]$filename, [string]$subject, [string]$object, [string]$polarity) {
  $row = @(@{subject=$subject; subject_type='Service'; subject_id=('svc:'+$subject);
             predicate='depends on'; object=$object; object_type='Service';
             object_id=('svc:'+$object); polarity=$polarity})
  $temp = Join-Path $out $filename
  [System.IO.File]::WriteAllText($temp,(JsonBody $row),(New-Object System.Text.UTF8Encoding($false)))
  $args = @('-sS','--fail','-X','POST','-H',('X-Dataset: '+$dataset))
  if ($env:UGI_DEMO_API_KEY) { $args += @('-H',('X-API-Key: '+$env:UGI_DEMO_API_KEY)) }
  $args += @('-F',('file=@'+$temp+';type=application/json'),($BaseUrl+'/api/uploads'))
  $response = & curl.exe @args
  if ($LASTEXITCODE -ne 0) { throw ('Upload failed: '+$filename) }
  return ($response | Out-String | ConvertFrom-Json)
}
try {
  $health = Invoke-RestMethod ($BaseUrl + '/health')
  Check 'feature flags enabled' ([bool]($health.guided_agent_enabled -and $health.memory_enabled)) $health
  $a = UploadEdge 'a.json' 'web' 'redis' 'positive'
  Check 'source ingested' ($a.claims -ge 1) $a
  $positive = PostJson '/api/agent/guided' @{query='Does web directly depend on redis?'}
  Check 'positive evidence verified' ($positive.status -eq 'COMPLETE' -and $positive.result.verdict -eq 'SOURCE_ASSERTED' -and $positive.read_count -ge 4 -and $positive.receipt_id) @{status=$positive.status; verdict=$positive.result.verdict; read_count=$positive.read_count}
  $posid = $positive.receipt_id
  $valid = GetJson ('/api/agent/receipts/'+$posid+'/freshness')
  Check 'initial receipt VALID' ($valid.freshness -eq 'VALID' -and $valid.safe_to_reuse) $valid
  $negative = PostJson '/api/agent/guided' @{query='Does redis directly depend on web?'}
  Check 'negative/unknown query captured' ($negative.status -eq 'COMPLETE' -and $negative.receipt_id) @{status=$negative.status; verdict=$negative.result.verdict}
  $b = UploadEdge 'b.json' 'redis' 'web' 'positive'
  Check 'new reverse edge ingested' ($b.claims -ge 1) $b
  $stale = GetJson ('/api/agent/receipts/'+$negative.receipt_id+'/freshness')
  Check 'old negative answer STALE' ($stale.freshness -eq 'STALE' -and -not $stale.safe_to_reuse) $stale
  $newAnswer = PostJson '/api/agent/guided' @{query='Does redis directly depend on web?'}
  Check 'fresh replan derives new evidence' ($newAnswer.status -eq 'COMPLETE' -and $newAnswer.result.verdict -eq 'SOURCE_ASSERTED') @{verdict=$newAnswer.result.verdict}
  $c = UploadEdge 'c.json' 'web' 'redis' 'negative'
  Check 'contradicting edge ingested' ($c.claims -ge 1) $c
  $unknown = GetJson ('/api/agent/receipts/'+$posid+'/freshness')
  Check 'opposing evidence escalates UNKNOWN' ($unknown.freshness -eq 'UNKNOWN' -and -not $unknown.safe_to_reuse) $unknown
  $report.result = 'PASS'
} catch {
  $report.result = 'FAIL'
  $report.error = $_.Exception.Message
  Write-Host ('FAIL: ' + $report.error) -ForegroundColor Red
} finally {
  $report.passed = @($report.checks | Where-Object { $_.pass }).Count
  $report.total = @($report.checks).Count
  $destination = Join-Path $out 'INTEGRATED_E2E_DECISION.json'
  [System.IO.File]::WriteAllText($destination,(JsonBody $report),(New-Object System.Text.UTF8Encoding($false)))
  Write-Host ('Report: '+$destination)
  Write-Host ('Disposable test dataset retained (not deleted): '+$dataset)
}
if ($report.result -ne 'PASS') { exit 1 }
Write-Host 'INTEGRATED HTTP/FalkorDB GUIDED+P5 E2E PASSED' -ForegroundColor Green
