@echo off
setlocal
if not exist "%~dp0.venv\Scripts\python.exe" (
  echo Run START.ps1 once to install the local environment. 1>&2
  exit /b 2
)
"%~dp0.venv\Scripts\python.exe" -m riposte %*
exit /b %errorlevel%
