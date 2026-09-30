param(
  [ValidateSet('check','install','backend','frontend','electron','db-check','report-check')]
  [string]$Action = 'check'
)
$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
$projectRoot = Split-Path $PSScriptRoot -Parent
$pythonPath = Join-Path $projectRoot 'backend/.venv/Scripts/python.exe'

function Assert-Exit([string]$Step) {
  if ($LASTEXITCODE -ne 0) { throw "$Step failed. Read the error above and retry." }
}

Push-Location $projectRoot
try {
  if ($Action -eq 'check') {
    $ok = $true
    if (Get-Command py -ErrorAction SilentlyContinue) {
      & py -3.12 --version
      if ($LASTEXITCODE -ne 0) { $ok = $false }
    } else { Write-Host 'MISSING: Python 3.12 with Windows py launcher'; $ok = $false }
    if (Get-Command node -ErrorAction SilentlyContinue) {
      $nodeVersion = (& node --version).TrimStart('v')
      Write-Host "System Node: $nodeVersion"
      if ([version]$nodeVersion -lt [version]'20.19.0') { Write-Host 'Node >=20.19 is required.'; $ok = $false }
    } else { Write-Host 'MISSING: Node.js'; $ok = $false }
    if (Get-Command npm.cmd -ErrorAction SilentlyContinue) {
      & npm.cmd --version
      if ($LASTEXITCODE -ne 0) { $ok = $false }
    } else { Write-Host 'MISSING: npm'; $ok = $false }
    if (Test-Path backend/.env) { Write-Host 'backend/.env: present (values not printed)' }
    else { Write-Host 'MISSING: backend/.env'; $ok = $false }
    Write-Host 'Required network: npm/PyPI, remote Supabase TCP 5432, and configured model HTTPS endpoints.'
    Write-Host 'No local PostgreSQL or Docker is required.'
    if (-not $ok) { exit 1 }
  } elseif ($Action -eq 'install') {
    if (-not (Test-Path $pythonPath)) { & py -3.12 -m venv backend/.venv; Assert-Exit 'Create venv' }
    & $pythonPath -m pip install -r backend/requirements.lock
    Assert-Exit 'Python dependencies'
    Push-Location .tools
    try { & npm.cmd ci; Assert-Exit 'Local Node installation' } finally { Pop-Location }
    Push-Location frontend
    try {
      & ../scripts/npm-local.cmd ci
      Assert-Exit 'Frontend dependencies'
      if (-not (Test-Path .env.local)) { Copy-Item .env.example .env.local }
    } finally { Pop-Location }
    Write-Host 'Dependencies ready. Existing environment files were not overwritten.'
  } elseif ($Action -in @('frontend','electron')) {
    Push-Location frontend
    try {
      if ($Action -eq 'frontend') { & ../scripts/npm-local.cmd run dev }
      else { & ../scripts/npm-local.cmd run electron:dev }
      Assert-Exit 'Frontend'
    } finally { Pop-Location }
  } else {
    if (-not (Test-Path $pythonPath)) { throw 'Run -Action install first.' }
    Push-Location backend
    try {
      if ($Action -eq 'backend') { & $pythonPath -m uvicorn app.main:app --host 127.0.0.1 --port 8000 }
      elseif ($Action -eq 'db-check') { & $pythonPath -m app.knowledge_cli check }
      elseif ($Action -eq 'report-check') { & $pythonPath -m app.report_cli check }
      Assert-Exit $Action
    } finally { Pop-Location }
  }
} finally { Pop-Location }
