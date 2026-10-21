@echo off
title CoverStore Workstation Keep-Awake Daemon
cd /d "%~dp0\.."
echo ======================================================
echo Starting CoverStore Workstation Keep-Awake Daemon...
echo Keeping PC active for remote Antigravity operations...
echo ======================================================
py -V >nul 2>&1
if %errorlevel% equ 0 (
    py scripts\keep_awake.py %*
) else (
    python scripts\keep_awake.py %*
)
pause
