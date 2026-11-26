[CmdletBinding()]
param(
    [switch]$Clean,
    [switch]$OwnerPortfolio
)

$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSCommandPath
Set-Location $root
if($Clean){Remove-Item -LiteralPath (Join-Path $root 'build') -Recurse -Force -ErrorAction SilentlyContinue;Remove-Item -LiteralPath (Join-Path $root 'dist') -Recurse -Force -ErrorAction SilentlyContinue}
# Ensure locally uploaded PDFs are actually readable in the shipped application.
python -m pip install "pypdf>=5,<8" pillow pywebview
if ($LASTEXITCODE -ne 0) { throw "PDF extraction dependency installation failed" }
python packaging\generate_icons.py
if ($LASTEXITCODE -ne 0) { throw 'App icon generation failed' }
# Customer distributions must not include the founder's bundled project registry.
# Explicit -OwnerPortfolio is reserved for an owner's separate private build.
$bundleSystem=Join-Path $root 'System'
if(-not $OwnerPortfolio){
    $bundleSystem=Join-Path $root 'build\customer-System'
    New-Item -ItemType Directory -Path $bundleSystem -Force | Out-Null
    Copy-Item -Path (Join-Path $root 'System\*') -Destination $bundleSystem -Recurse -Force
    [System.IO.File]::WriteAllText(
        (Join-Path $bundleSystem 'project-registry.json'),
        '{"projects":[]}',
        (New-Object System.Text.UTF8Encoding($false))
    )
}
python -m PyInstaller --noconfirm --clean --onedir --windowed --icon "$root\packaging\icons\AIBO.ico" --name AIBO `
  --specpath build `
  --add-data "$root\Control-Centre;Control-Centre" `
  --add-data "$bundleSystem;System" `
  --add-data "$root\Industry-Packs;Industry-Packs" `
  --add-data "$root\runtime\agents.json;runtime" `
  --add-data "$root\runtime\connectors.json;runtime" `
  --collect-all playwright `
  --collect-all webview `
  runtime\windows_app.py
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed with exit code $LASTEXITCODE" }
Write-Host 'Built local package: dist\AIBO\AIBO.exe'
