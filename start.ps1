param([int]$Port = 8000)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$projectPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $projectPython)) { throw 'Run .\setup.ps1 first.' }
& $projectPython manage.py migrate --noinput
if ($LASTEXITCODE -ne 0) { throw 'Database migration failed.' }
Write-Host "`nFridgewise: http://127.0.0.1:$Port/" -ForegroundColor Green
Write-Host 'Demo: demo / FreshStart!2026'
Write-Host 'Email reminders are manual: use the button in a user fridge in Administration.'
Write-Host 'Press Ctrl+C to stop the app.'
& $projectPython -u manage.py runserver "127.0.0.1:$Port" --noreload
