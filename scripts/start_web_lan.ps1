param(
    [int]$Port = 8080,
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Web = Join-Path $Root "web"
$Python = Join-Path $Root ".venv\Scripts\python.exe"

if (-not (Get-Command node.exe -ErrorAction SilentlyContinue)) {
    throw "Node.js was not found. Install Node.js 24 LTS and reopen PowerShell."
}
if (-not (Test-Path $Python)) {
    throw "Python virtual environment .venv was not found. Follow README.md to create it first."
}

if (-not $SkipBuild) {
    & $Python (Join-Path $Root "scripts\export_web_puzzles.py")
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    Push-Location $Web
    try {
        if (-not (Test-Path "node_modules")) { & npm.cmd ci }
        & npm.cmd run build
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
    finally {
        Pop-Location
    }
}

Push-Location $Web
try {
    & node.exe scripts/serve-lan.mjs $Port
}
finally {
    Pop-Location
}
