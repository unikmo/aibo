[CmdletBinding()]
param([switch]$AllowUnsignedDevelopment)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSCommandPath
Set-Location $root
$app = Join-Path $root 'dist\AIBO\AIBO.exe'
if (!(Test-Path $app)) { throw 'AIBO.exe missing; run build-windows.ps1 first.' }
# Signing only with a verified publisher certificate; no Smart App Control bypass.
$signature = Get-AuthenticodeSignature -LiteralPath $app
if (!$AllowUnsignedDevelopment -and $signature.Status -ne 'Valid') {
  throw 'AIBO.exe must have a valid Authenticode publisher signature for public distribution.'
}
$compiler = @(
  "$env:ProgramFiles(x86)\Inno Setup 6\ISCC.exe",
  "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
  'ISCC.exe'
) | Where-Object { $_ -and (Test-Path $_ -ErrorAction SilentlyContinue -PathType Leaf) } | Select-Object -First 1
if (!$compiler) { throw 'Inno Setup 6 compiler not found. Installer packaging requires Inno Setup.' }
& $compiler 'packaging\windows\AIBO.iss'
if ($LASTEXITCODE -ne 0) { throw 'Windows installer build failed.' }
$setup = 'dist\installer\AIBO-Control-Centre-Windows-Setup.exe'
if (!$AllowUnsignedDevelopment) {
  $setupSignature=Get-AuthenticodeSignature -LiteralPath $setup
  if ($setupSignature.Status -ne 'Valid') {
    throw 'The installer must also be signed before public release.'
  }
}
Write-Host "Built installer: $setup"
