@echo off
REM Windows: double-click to stop Youtube Card Reader.
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\stop.ps1"
set "exitCode=%ERRORLEVEL%"
pause
exit /b %exitCode%
