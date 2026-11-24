[CmdletBinding()]
param()
$ErrorActionPreference='Stop'
$root=Split-Path (Split-Path -Parent $PSCommandPath) -Parent
Set-Location $root
$thumb=($env:AIBO_WINDOWS_SIGNING_THUMBPRINT -replace '\s','').ToUpperInvariant()
if ($thumb -notmatch '^[A-F0-9]{40}$') {
  throw 'A real individual-publisher signing certificate thumbprint is required.'
}
$certificate = Get-ChildItem "Cert:\CurrentUser\My\$thumb" -ErrorAction SilentlyContinue
if (!$certificate) { $certificate = Get-ChildItem "Cert:\LocalMachine\My\$thumb" -ErrorAction SilentlyContinue }
if (!$certificate -or !$certificate.HasPrivateKey) {
  throw 'Approved publisher certificate and signing private key must be available in Windows certificate store.'
}
$signTool=if($env:AIBO_SIGNTOOL_PATH){ $env:AIBO_SIGNTOOL_PATH } else {'signtool.exe'}
$folder=Join-Path $root 'dist\AIBO'
if (!(Test-Path (Join-Path $folder 'AIBO.exe'))) { throw 'First build the AIBO Windows application.' }
$files=Get-ChildItem $folder -File -Recurse | Where-Object { $_.Extension.ToLowerInvariant() -in @('.exe','.dll','.pyd') }
foreach ($file in $files) {
  $existing=Get-AuthenticodeSignature -LiteralPath $file.FullName
  if ($existing.Status -eq 'Valid') { continue } # Preserve valid vendor signatures.
  & $signTool sign /sha1 $thumb /fd SHA256 /tr 'http://timestamp.digicert.com' /td SHA256 $file.FullName
  if ($LASTEXITCODE -ne 0) { throw "Failed signing $($file.Name)" }
  $verify=Get-AuthenticodeSignature -LiteralPath $file.FullName
  if ($verify.Status -ne 'Valid' -or $verify.SignerCertificate.Thumbprint -ne $thumb) {
    throw "Invalid signature on $($file.Name)"
  }
}
$main=Get-AuthenticodeSignature -LiteralPath (Join-Path $folder 'AIBO.exe')
if ($main.Status -ne 'Valid' -or $main.SignerCertificate.Thumbprint -ne $thumb) {
  throw 'AIBO main executable lacks the approved individual-publisher signature.'
}
Write-Host "Signed/verified $($files.Count) portable executable components"
