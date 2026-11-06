@echo off
setlocal
cd /d "%~dp0"
title MandateTrail - Orbital Intelligence
echo.
echo  MandateTrail / Orbital Intelligence / SYNTHETIC SANDBOX
echo  First launch downloads Python and Node dependencies. Internet is required.
echo.
where powershell.exe >nul 2>nul
if errorlevel 1 goto :noPowerShell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start.ps1" %*
if errorlevel 1 (
  echo.
  echo Startup failed. Read the error above and logs in the logs folder.
  if not "%MT_NO_PAUSE%"=="1" pause
  exit /b 1
)
exit /b 0
:noPowerShell
echo Windows PowerShell is required.
pause
exit /b 1
