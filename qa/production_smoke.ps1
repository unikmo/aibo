# AIBO stage 7: post-install smoke on the user's real local instance.
# Read-only HTTP checks; never starts paid provider calls or publishes content.
param(
  [string]$BaseUrl = "http://127.0.0.1:8766"
)
$ErrorActionPreference = "Stop"
$BaseUrl = $BaseUrl.TrimEnd('/')
if ($BaseUrl -notmatch '^http://(?:127\.0\.0\.1|localhost):\d+$') {
  throw "Only a local AIBO server URL is allowed."
}
$paths = @("/v3/", "/v3/app.js", "/api/products/custom", "/api/ai-providers", "/api/portfolio/custom")
foreach ($path in $paths) {
  $r = Invoke-WebRequest -Uri ($BaseUrl + $path) -UseBasicParsing -TimeoutSec 8
  if ($r.StatusCode -ne 200) { throw "FAIL: $path returned HTTP $($r.StatusCode)" }
  if ($r.Headers['X-Frame-Options'] -ne 'DENY') { throw "FAIL: Security header missing for $path" }
  Write-Host "PASS $path"
}
$page = (Invoke-WebRequest -Uri ($BaseUrl + "/v3/") -UseBasicParsing -TimeoutSec 8).Content
if ($page -notmatch 'id="newProjectBtn"' -or $page -notmatch 'id="soniPrompt"') {
  throw "FAIL: The expected new Control Centre bundle is not active"
}
if ($page -notmatch '#242927') { throw "FAIL: Dark Soni stylesheet is missing" }
Write-Host "STAGE 7 PASS: AIBO local installation accessible; correct UI bundle and API paths detected."
Write-Host "This smoke test does not certify user acceptance, CLI authentication or live external integrations."
