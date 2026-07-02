$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    python -m venv (Join-Path $root ".venv")
    & $python -m pip install -e "$root"
}
& $python -m shuhui

