$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    python -m venv (Join-Path $root ".venv")
}
& $python -m pip install -e "${root}[dev]"
Push-Location $root
try {
    & $python -m PyInstaller --noconfirm --clean --onefile --windowed --name "Shuhui" --collect-all ortools --collect-all reportlab scripts\gui_entry.py
}
finally {
    Pop-Location
}
