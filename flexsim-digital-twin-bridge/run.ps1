#Requires -Version 5.1
<#
    Creates the virtual environment if missing, installs dependencies,
    and launches the FastAPI bridge on 127.0.0.1:8000.
#>

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

$VenvPath = Join-Path $ScriptDir ".venv"
$VenvPython = Join-Path $VenvPath "Scripts\python.exe"

if (-not (Test-Path $VenvPython)) {
    Write-Host "Creating virtual environment at .venv ..."
    python -m venv $VenvPath
}

Write-Host "Installing/updating dependencies ..."
& $VenvPython -m pip install --upgrade pip --quiet
& $VenvPython -m pip install -r (Join-Path $ScriptDir "requirements.txt") --quiet

Write-Host "Starting flexsim-digital-twin-bridge on http://127.0.0.1:8000 ..."
& $VenvPython -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
