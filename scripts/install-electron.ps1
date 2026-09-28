param([switch]$UseMirror)
$ErrorActionPreference = 'Stop'
# Windows x64 fallback; writes only to repository artifacts and node_modules.
$repoRoot = Split-Path $PSScriptRoot -Parent
$electronDir = Join-Path $repoRoot 'frontend/node_modules/electron'
$package = Get-Content (Join-Path $electronDir 'package.json') -Raw | ConvertFrom-Json
$checksums = Get-Content (Join-Path $electronDir 'checksums.json') -Raw | ConvertFrom-Json
$archiveName = "electron-v$($package.version)-win32-x64.zip"
$expected = $checksums.$archiveName
if (-not $expected) { throw 'No trusted checksum for Windows x64 in installed Electron package.' }
$artifactDir = Join-Path $repoRoot 'artifacts'
New-Item -ItemType Directory -Force -Path $artifactDir | Out-Null
$archive = Join-Path $artifactDir $archiveName
$valid = (Test-Path -LiteralPath $archive) -and ((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash -eq $expected)
if (-not $valid) {
    $url = "https://github.com/electron/electron/releases/download/v$($package.version)/$archiveName"
    if ($UseMirror) { $url = "https://npmmirror.com/mirrors/electron/$($package.version)/$archiveName" }
    Write-Host "Downloading $archiveName; checksum verification is mandatory."
    & curl.exe -fLsS --connect-timeout 20 --max-time 600 --retry 2 -o $archive $url
    if ($LASTEXITCODE -ne 0) { throw 'Download failed. Retry when network access is available.' }
}
if ((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash -ne $expected) {
    throw 'SHA-256 mismatch. Refusing to extract.'
}
Expand-Archive -LiteralPath $archive -DestinationPath (Join-Path $electronDir 'dist') -Force
Set-Content -LiteralPath (Join-Path $electronDir 'path.txt') -Value 'electron.exe' -NoNewline -Encoding ascii
Write-Host "Installed Electron $($package.version); SHA-256 verified: $expected"
