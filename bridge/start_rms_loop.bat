@echo off
REM Double-click this file to keep the RMS scheduler running: it picks
REM and dispatches a robot every 5 seconds against real FlexSim/mock
REM telemetry, so the dashboard's "RMS Scheduling Decision" panel
REM actually updates on its own instead of showing one static run.
REM Run this AFTER start.bat (the bridge must already be running) and
REM after start_ros2_sim.bat or a real FlexSim run (there must be robot
REM telemetry for it to schedule against).

cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Bridge is not set up yet. Run start.bat first.
    pause
    exit /b 1
)
.venv\Scripts\python.exe -u ..\examples\live_flexsim_rms_demo.py --loop
pause
