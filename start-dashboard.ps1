$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path

if (-not (Test-Path "$Root\backend\.venv\Scripts\python.exe")) {
    Write-Host "Backend environment not found. Run the setup steps in README.md first." -ForegroundColor Yellow
    exit 1
}

if (-not (Test-Path "$Root\frontend\node_modules")) {
    Write-Host "Frontend dependencies not found. Run npm install in frontend first." -ForegroundColor Yellow
    exit 1
}

$Node = Get-Command node.exe -ErrorAction SilentlyContinue
if (-not $Node) {
    Write-Host "Node.js was not found. Restart PowerShell or install Node.js 20+." -ForegroundColor Yellow
    exit 1
}

$Backend = Start-Process `
    -FilePath "$Root\backend\.venv\Scripts\python.exe" `
    -ArgumentList "-m", "uvicorn", "app.main:app", "--reload", "--port", "8001" `
    -WorkingDirectory "$Root\backend" `
    -PassThru

$Frontend = Start-Process `
    -FilePath $Node.Source `
    -ArgumentList "$Root\frontend\node_modules\vite\bin\vite.js", "--host", "127.0.0.1", "--port", "5173" `
    -WorkingDirectory "$Root\frontend" `
    -PassThru

Write-Host "Dashboard services started. Backend PID: $($Backend.Id), Frontend PID: $($Frontend.Id)" -ForegroundColor Green
Write-Host "Open http://localhost:5173" -ForegroundColor Green
