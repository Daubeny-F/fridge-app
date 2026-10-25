param([string]$Python = '')
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
function Invoke-Checked {
    param([string]$Executable, [string[]]$Arguments)
    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Command failed: $Executable $Arguments" }
}
if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
    if (-not $Python) {
        $bundledPython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
        if (Test-Path -LiteralPath $bundledPython) { $Python = $bundledPython }
        elseif (Get-Command py -ErrorAction SilentlyContinue) {
            & py -3 -c "import sys; print(sys.executable)" | ForEach-Object { $Python = $_ }
            if ($LASTEXITCODE -ne 0) { throw 'Install Python 3.10 or later, or pass -Python C:\path\to\python.exe.' }
        }
        elseif (Get-Command python -ErrorAction SilentlyContinue) { $Python = (Get-Command python).Source }
        else { throw 'Install Python 3.10 or later, or pass -Python C:\path\to\python.exe.' }
    }
    Invoke-Checked -Executable $Python -Arguments @('-m','venv','.venv')
}
$projectPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
Invoke-Checked -Executable $projectPython -Arguments @('-m','pip','install','-r','requirements.txt')
Invoke-Checked -Executable $projectPython -Arguments @('manage.py','migrate')
Invoke-Checked -Executable $projectPython -Arguments @('manage.py','seed_demo')
Invoke-Checked -Executable $projectPython -Arguments @('manage.py','check')
Write-Host "`nAll set. Save the admin password above, then run: .\start.ps1" -ForegroundColor Green
