# Run manually in PowerShell after reviewing installer sources and requirements.
# This script installs no software and never requests or stores secrets.
$ErrorActionPreference = 'Continue'
Write-Host 'AIBO Windows prerequisites and credential discovery'
foreach ($command in @('python', 'git', 'node', 'npm', 'codex', 'claude', 'vercel')) {
  $found = Get-Command $command -ErrorAction SilentlyContinue
  if ($found) { Write-Host "OK   $command : $($found.Source)" }
  else { Write-Host "MISSING $command" }
}
foreach ($key in @('OPENAI_API_KEY','ANTHROPIC_API_KEY','VERCEL_TOKEN')) {
  if ([Environment]::GetEnvironmentVariable($key)) { Write-Host "SET   $key" }
  else { Write-Host "UNSET $key" }
}
Write-Host 'To install with trusted official registries after review:'
Write-Host 'npm install -g @openai/codex @anthropic-ai/claude-code vercel'
Write-Host 'python -m pip install playwright; python -m playwright install chromium'
Write-Host 'Authenticate the Codex/Claude/Vercel CLIs using their supported login commands.'
Write-Host 'Use user-scoped environment variables or an OS secret manager; never commit API keys.'
python runtime/operations.py doctor
