@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if errorlevel 1 (
  python runtime\control_server.py --port 8765 --open-browser
) else (
  py -3 runtime\control_server.py --port 8765 --open-browser
)

if errorlevel 1 pause
