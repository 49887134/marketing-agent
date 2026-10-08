param(
  [ValidateSet('check','install','backend','frontend','electron','verify')]
  [string]$Action = 'check'
)
$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
$projectRoot = Split-Path $PSScriptRoot -Parent
if ($Action -eq 'verify') {
  Push-Location (Join-Path $projectRoot 'backend')
  try {
    & ./.venv/Scripts/python.exe -m app.verify_agent
    if ($LASTEXITCODE -ne 0) { throw 'Real verification failed. Inspect artifacts/lesson3-real-*.json.' }
  } finally { Pop-Location }
} else {
  & (Join-Path $PSScriptRoot 'project.ps1') -Action $Action
}
