@echo off
title CoverStore 20-Min Auto-Sync Daemon
cd /d "%~dp0\.."
echo ======================================================
echo Starting CoverStore 20-Minute Git Auto-Sync Daemon...
echo Repository: %CD%
echo Synchronizing every 20 minutes (:00, :20, :40)
echo ======================================================
python scripts\auto_sync.py
pause
