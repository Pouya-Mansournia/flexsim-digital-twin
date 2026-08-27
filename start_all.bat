@echo off
REM Double-click this file to start EVERYTHING for the digital twin at
REM once: the bridge (+ dashboard, opened automatically), the mock
REM real-environment robot fleet, and a repeating RMS scheduling loop so
REM the dashboard's "RMS Scheduling Decision" panel keeps updating on
REM its own, the same way the rest of the dashboard does.
REM
REM Each piece still works completely on its own, exactly as before:
REM   bridge\start.bat                                    just the bridge + dashboard
REM   bridge\start_ros2_sim.bat                            just the mock robot fleet
REM   bridge\start_rms_loop.bat                            just the repeating RMS scheduler
REM   python examples\live_flexsim_rms_demo.py             one RMS scheduling run, then exit
REM This file is only a convenience wrapper around those. It waits for
REM each step to actually be ready instead of guessing a fixed delay,
REM since first-time setup (creating the virtual environment, installing
REM dependencies) can take well over a minute.

cd /d "%~dp0"

echo ==================================================
echo  FlexSim Digital Twin: starting everything
echo ==================================================
echo.

echo [1/3] Starting the bridge (new window: "FlexSim Bridge")...
start "FlexSim Bridge" cmd /k "cd /d bridge && start.bat"

echo Waiting for the bridge to come up (this can take a minute or more
echo on first run, while it sets up its virtual environment)...
set /a bridge_tries=0
:wait_for_bridge
powershell -NoProfile -Command "try { Invoke-RestMethod -Uri http://127.0.0.1:8000/health -TimeoutSec 2 | Out-Null; exit 0 } catch { exit 1 }" >nul 2>nul
if %errorlevel%==0 goto bridge_ready
set /a bridge_tries+=1
if %bridge_tries% GEQ 90 (
    echo.
    echo The bridge did not come up after a while. Check the "FlexSim Bridge"
    echo window for errors, then run this file again once it's up, or run
    echo the remaining steps yourself:
    echo   bridge\start_ros2_sim.bat
    echo   python examples\live_flexsim_rms_demo.py
    goto end
)
timeout /t 2 /nobreak >nul
goto wait_for_bridge
:bridge_ready
echo Bridge is up.
echo.

echo [2/3] Starting the mock real-environment fleet (new window: "ROS2 Mock Fleet")...
start "ROS2 Mock Fleet" cmd /k "cd /d bridge && start_ros2_sim.bat"

echo Waiting for the mock fleet's telemetry to start flowing...
set /a robot_tries=0
:wait_for_robots
powershell -NoProfile -Command "try { $r = Invoke-RestMethod -Uri http://127.0.0.1:8000/api/v1/real/state -TimeoutSec 2; if ($r.has_data -and $r.telemetry.robots.PSObject.Properties.Count -gt 0) { exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>nul
if %errorlevel%==0 goto robots_ready
set /a robot_tries+=1
if %robot_tries% GEQ 30 (
    echo.
    echo No robot telemetry showed up yet. Starting the RMS scheduler loop
    echo anyway: it retries on its own every 5 seconds and will start
    echo scheduling as soon as telemetry arrives ^(from the "ROS2 Mock
    echo Fleet" window or a real FlexSim run^).
    goto start_rms_loop
)
timeout /t 1 /nobreak >nul
goto wait_for_robots
:robots_ready
echo Robot telemetry is flowing.
echo.

:start_rms_loop
echo [3/3] Starting the RMS scheduling loop (new window: "RMS Scheduler")...
echo It picks and dispatches a robot every 5 seconds, so the dashboard's
echo "RMS Scheduling Decision" panel keeps updating on its own. Scheduled
echo against the mock fleet this file just started (--source real), since
echo there's no guarantee a real FlexSim model is running too.
start "RMS Scheduler" cmd /k "cd /d bridge && start_rms_loop.bat --source real"

:end
echo.
echo ==================================================
echo Dashboard: http://127.0.0.1:8000/dashboard
echo   ^(already opened automatically by start.bat^)
echo.
echo Close the "FlexSim Bridge", "ROS2 Mock Fleet", or "RMS Scheduler"
echo windows to stop those pieces.
echo ==================================================
pause
