@echo off
setlocal
powershell.exe -NoProfile -File "%~dp0START.ps1" %*
set "RIPOSTE_EXIT=%errorlevel%"
if not "%RIPOSTE_EXIT%"=="0" pause
exit /b %RIPOSTE_EXIT%
