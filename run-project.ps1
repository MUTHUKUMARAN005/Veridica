$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "=== 1. Setting up Python Backend ===" -ForegroundColor Cyan
Set-Location "$Root\backend"
if (-not (Test-Path ".venv")) {
    python -m venv .venv
}
& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
& ".\.venv\Scripts\pip.exe" install -r requirements-dev.txt

Write-Host "=== 2. Running Backend Unit & Acceptance Tests ===" -ForegroundColor Cyan
& ".\.venv\Scripts\pytest.exe"
& ".\.venv\Scripts\ruff.exe" check .

Write-Host "=== 3. Setting up Frontend ===" -ForegroundColor Cyan
Set-Location "$Root\frontend"
if (-not (Test-Path "node_modules")) {
    npm install
}

Write-Host "=== 4. Running Frontend Unit Tests & Build ===" -ForegroundColor Cyan
npm test
npm run build

Write-Host "=== 5. Starting Veridica Backend (Port 8000) & Frontend (Port 5173) ===" -ForegroundColor Green
Start-Process -WorkingDirectory "$Root\backend" -FilePath "$Root\backend\.venv\Scripts\uvicorn.exe" -ArgumentList "app.main:app --host 127.0.0.1 --port 8000 --reload"
npm run dev -- --host 127.0.0.1 --port 5173
