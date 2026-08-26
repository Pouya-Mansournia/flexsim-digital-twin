@echo off
REM Double-click this file to start the mock real-environment robot fleet.
REM Run this AFTER start.bat (the bridge must already be running).

cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Bridge is not set up yet. Run start.bat first.
    pause
    exit /b 1
)
.venv\Scripts\python.exe -u ros2_sim\simulator.py --robots 2
pause
