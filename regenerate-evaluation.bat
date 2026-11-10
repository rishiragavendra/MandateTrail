@echo off
setlocal
rem This launcher lives in the project root, so %~dp0 is already the project root.
cd /d "%~dp0"
title MandateTrail - regenerate ablation evaluation
echo.
echo  Regenerating docs\evaluation-results.json against the running backend.
echo  Start the app with run.bat first; this takes a couple of minutes.
echo.
if not exist ".venv\Scripts\python.exe" (
  echo  Virtual environment not found at "%CD%\.venv".
  echo  Run run.bat once first, then retry.
  pause
  exit /b 1
)
if not exist "backend\data\DEMO_CREDENTIALS.txt" (
  echo  Demo credentials not found. Start the app with run.bat once first.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" "scripts\evaluate.py" --output "docs\evaluation-results.json"
if errorlevel 1 (
  echo.
  echo  Evaluation failed. Check that run.bat is running and port 8000 is up.
  pause
  exit /b 1
)
echo.
echo  Done. docs\evaluation-results.json rewritten.
pause
