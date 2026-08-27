@echo off
REM Double-click this file to keep the RMS scheduler running: it picks
REM and dispatches a robot every 5 seconds, so the dashboard's "RMS
REM Scheduling Decision" panel actually updates on its own instead of
REM showing one static run.
REM
REM Defaults to scheduling against real FlexSim telemetry, which needs
REM an actual FlexSim model running and posting to the bridge. If
REM you're only running the mock fleet (start_ros2_sim.bat) and want to
REM see decisions change without FlexSim, pass --source real:
REM   start_rms_loop.bat --source real
REM
REM Run this AFTER start.bat (the bridge must already be running) and
REM after there's robot telemetry to schedule against (a real FlexSim
REM run, or start_ros2_sim.bat with --source real above).

cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Bridge is not set up yet. Run start.bat first.
    pause
    exit /b 1
)
.venv\Scripts\python.exe -u ..\examples\live_flexsim_rms_demo.py --loop %*
pause
