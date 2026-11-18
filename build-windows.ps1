[CmdletBinding()]
param(
    [switch]$Clean
)

$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSCommandPath
Set-Location $root
if($Clean){Remove-Item -LiteralPath (Join-Path $root 'build') -Recurse -Force -ErrorAction SilentlyContinue;Remove-Item -LiteralPath (Join-Path $root 'dist') -Recurse -Force -ErrorAction SilentlyContinue}
python -m PyInstaller --noconfirm --clean --onedir --name AIBO `
  --specpath build `
  --add-data "$root\Control-Centre;Control-Centre" `
  --add-data "$root\System;System" `
  --add-data "$root\Industry-Packs;Industry-Packs" `
  --add-data "$root\runtime\agents.json;runtime" `
  --collect-all playwright `
  runtime\windows_app.py
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed with exit code $LASTEXITCODE" }
Write-Host 'Built local package: dist\AIBO\AIBO.exe'
