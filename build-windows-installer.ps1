[CmdletBinding()]
param([switch]$AllowUnsignedDevelopment)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSCommandPath
Set-Location $root
$app = Join-Path $root 'dist\AIBO\AIBO.exe'
if (!(Test-Path $app)) { throw 'AIBO.exe missing; run build-windows.ps1 first.' }
# Signing only with a verified publisher certificate; no Smart App Control bypass.
if (!$AllowUnsignedDevelopment) {
  # The owner controls the publisher certificate. Sign only when this trusted
  # certificate exists; never generate an untrusted self-signed substitute.
  & (Join-Path $root 'packaging\windows\sign-app.ps1')
  if ($LASTEXITCODE -ne 0) { throw 'Signing of AIBO application components failed.' }
}
$signature = Get-AuthenticodeSignature -LiteralPath $app
if (!$AllowUnsignedDevelopment) {
  $expected = ($env:AIBO_WINDOWS_SIGNING_THUMBPRINT -replace '\\s','').ToUpperInvariant()
  if ($expected -notmatch '^[A-F0-9]{40}$' -or $signature.Status -ne 'Valid' -or $signature.SignerCertificate.Thumbprint -ne $expected) {
    throw 'AIBO.exe must have a valid Authenticode signature from the approved individual publisher.'
  }
}
$compiler = @(
  "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
  "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
  'ISCC.exe'
) | Where-Object { $_ -and (Test-Path $_ -ErrorAction SilentlyContinue -PathType Leaf) } | Select-Object -First 1
if (!$compiler) { throw 'Inno Setup 6 compiler not found. Installer packaging requires Inno Setup.' }
& $compiler 'packaging\windows\AIBO.iss'
if ($LASTEXITCODE -ne 0) { throw 'Windows installer build failed.' }
$setup = 'dist\installer\AIBO-Control-Centre-Windows-Setup.exe'
if (!$AllowUnsignedDevelopment) {
  # Sign using only an owner-provisioned Windows certificate. Never store
  # certificate private keys or secrets in source or CI artifacts.
  $thumbprint = ($env:AIBO_WINDOWS_SIGNING_THUMBPRINT -replace '\\s','').ToUpperInvariant()
  if (!$thumbprint -or $thumbprint -notmatch '^[A-F0-9]{40}$') {
    throw 'A validated Windows code-signing certificate thumbprint is required.'
  }
  $signTool = if ($env:AIBO_SIGNTOOL_PATH) { $env:AIBO_SIGNTOOL_PATH } else { 'signtool.exe' }
  & $signTool sign /sha1 $thumbprint /fd SHA256 /tr "http://timestamp.digicert.com" /td SHA256 $setup
  if ($LASTEXITCODE -ne 0) { throw 'Installer signing failed.' }
  $setupSignature=Get-AuthenticodeSignature -LiteralPath $setup
  if ($setupSignature.Status -ne 'Valid' -or $setupSignature.SignerCertificate.Thumbprint -ne $thumbprint) {
    throw 'Installer signature invalid or does not match approved individual publisher certificate.'
  }
}
Write-Host "Built installer: $setup"
