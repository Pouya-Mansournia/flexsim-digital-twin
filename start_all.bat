@echo off
REM Double-click this file to start EVERYTHING for the digital twin at
REM once: the bridge (+ dashboard, opened automatically), the mock
REM real-environment robot fleet, and one RMS scheduling run so the
REM dashboard's "RMS Scheduling Decision" panel has something to show.
REM
REM Each piece still works completely on its own, exactly as before:
REM   bridge\start.bat                            just the bridge + dashboard
REM   bridge\start_ros2_sim.bat                    just the mock robot fleet
REM   python examples\live_flexsim_rms_demo.py     just one RMS run
REM This file is only a convenience wrapper around those three.

cd /d "%~dp0"

echo ==================================================
echo  FlexSim Digital Twin: starting everything
echo ==================================================
echo.

echo [1/3] Starting the bridge (new window: "FlexSim Bridge")...
start "FlexSim Bridge" cmd /k "cd /d bridge && start.bat"

echo Waiting for the bridge to come up...
timeout /t 8 /nobreak >nul

echo [2/3] Starting the mock real-environment fleet (new window: "ROS2 Mock Fleet")...
start "ROS2 Mock Fleet" cmd /k "cd /d bridge && start_ros2_sim.bat"

echo Waiting for telemetry to start flowing...
timeout /t 5 /nobreak >nul

echo [3/3] Running one RMS scheduling decision...
if exist "bridge\.venv\Scripts\python.exe" (
    bridge\.venv\Scripts\python.exe examples\live_flexsim_rms_demo.py
) else (
    echo Bridge virtual environment not found yet ^(first-time setup may still
    echo be running in the "FlexSim Bridge" window^); skipping the RMS demo run.
    echo Run it yourself once that finishes:
    echo   python examples\live_flexsim_rms_demo.py
)

echo.
echo ==================================================
echo Dashboard: http://127.0.0.1:8000/dashboard
echo   ^(already opened automatically by start.bat^)
echo.
echo Close the "FlexSim Bridge" and "ROS2 Mock Fleet" windows to stop them.
echo ==================================================
pause
