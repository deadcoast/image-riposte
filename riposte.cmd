@echo off
setlocal
if not exist "%~dp0.venv\Scripts\python.exe" (
  echo Run INSTALL.ps1 to install the local environment, then START.cmd to open the menu. 1>&2
  exit /b 2
)
"%~dp0.venv\Scripts\python.exe" -m riposte %*
exit /b %errorlevel%
