[CmdletBinding()]
param(
    [ValidateSet('Desktop','StartMenu')]
    [string]$Location='Desktop'
)

$root=Split-Path -Parent $PSCommandPath
$launcher=Join-Path $root 'Start-AIBO-Control-Centre.cmd'
if (!(Test-Path -LiteralPath $launcher)) {
    throw 'Start-AIBO-Control-Centre.cmd was not found beside this installer.'
}

$target=if ($Location -eq 'Desktop') {
    [Environment]::GetFolderPath('Desktop')
} else {
    Join-Path ([Environment]::GetFolderPath('StartMenu')) 'Programs'
}
$shortcut=Join-Path $target 'AIBO Control Centre.lnk'
$shell=New-Object -ComObject WScript.Shell
$link=$shell.CreateShortcut($shortcut)
$link.TargetPath=$env:ComSpec
$link.Arguments='/c ""'+$launcher+'""'
$link.WorkingDirectory=$root
$link.Description='Start the local AIBO Control Centre'
$link.Save()
Write-Host "Created $shortcut"
