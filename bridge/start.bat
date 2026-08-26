@echo off
REM Double-click this file to set up (first run only) and start the bridge.
REM Opens the dashboard in your browser automatically once the server is up.

cd /d "%~dp0"
start "" powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Sleep -Seconds 6; Start-Process 'http://127.0.0.1:8000/dashboard'"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run.ps1"
pause
