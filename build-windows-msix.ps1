[CmdletBinding()]
param([switch]$Development)
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSCommandPath
Set-Location $root
$source=Join-Path $root 'dist\AIBO'
if (!(Test-Path (Join-Path $source 'AIBO.exe'))) { throw 'Build the desktop executable before packaging MSIX.' }
if ($Development) {
  # Structural test only. Unsigned development MSIX cannot be installed as trusted.
  $identity='AIBO.ControlCentre.Development'
  $publisher='CN=AIBO Development'
  $display='AIBO Development (unsigned)'
} else {
  # Must match EXACT reserved identity and publisher issued by Microsoft Partner Center.
  $identity=$env:AIBO_MSIX_IDENTITY
  $publisher=$env:AIBO_MSIX_PUBLISHER
  $display=$env:AIBO_MSIX_PUBLISHER_DISPLAY
  if (!$identity -or !$publisher -or !$display) {
    throw 'Store identity/publisher not configured. No guessed legal identity is permitted.'
  }
}
if ($identity -notmatch '^[A-Za-z0-9.-]{3,64}$' -or $publisher -notmatch '^CN=.+') {
  throw 'Invalid MSIX identity or publisher.'
}
$layout=Join-Path $root 'dist\msix-layout'
if (Test-Path $layout) { Remove-Item $layout -Recurse -Force }
New-Item -ItemType Directory -Path $layout | Out-Null
Copy-Item -Path (Join-Path $source '*') -Destination $layout -Recurse -Force
$assets=Join-Path $layout 'Assets'
New-Item -ItemType Directory -Path $assets | Out-Null
foreach ($image in @('StoreLogo.png','Square44x44Logo.png','Square150x150Logo.png')) {
  Copy-Item (Join-Path $root "packaging\icons\msix\$image") -Destination $assets
}
$manifest=Get-Content 'packaging\windows\AppxManifest.xml' -Raw
$manifest=$manifest.Replace('__AIBO_PACKAGE_ID__',$identity).Replace('__AIBO_PUBLISHER__',$publisher).Replace('__AIBO_PUBLISHER_DISPLAY__',$display)
[xml]$parsed=$manifest
$manifest | Set-Content -LiteralPath (Join-Path $layout 'AppxManifest.xml') -Encoding utf8
$sdk=Join-Path "${env:ProgramFiles(x86)}" 'Windows Kits\10\bin'
$tool=Get-ChildItem -LiteralPath $sdk -Filter MakeAppx.exe -Recurse -ErrorAction SilentlyContinue |
  Where-Object { $_.FullName -match '\\x64\\' } |
  Sort-Object -Property FullName -Descending |
  Select-Object -First 1
if (!$tool) { throw 'Windows SDK MakeAppx.exe not installed.' }
$out=Join-Path $root 'dist\AIBO-Control-Centre-Windows-x64.msix'
& $tool.FullName pack /d $layout /p $out /o
if ($LASTEXITCODE -ne 0) { throw 'MSIX packaging failed.' }
# Unpack to a fresh directory and verify payload + manifest.
$check=Join-Path $root 'dist\msix-qa-unpacked'
if (Test-Path $check) { Remove-Item $check -Recurse -Force }
& $tool.FullName unpack /p $out /d $check /o
if ($LASTEXITCODE -ne 0 -or !(Test-Path (Join-Path $check 'AIBO.exe')) -or !(Test-Path (Join-Path $check '_internal\Control-Centre\v3\index.html'))) {
  throw 'MSIX payload verification failed.'
}
Write-Host "MSIX generated and unpack-tested: $out"
if ($Development) {
  Write-Host 'WARNING: UNTRUSTED DEVELOPMENT BUILD. Do not sideload or publish.'
} else {
  Write-Host 'Store submission requires verified Microsoft Partner Center publisher identity and review.'
}
