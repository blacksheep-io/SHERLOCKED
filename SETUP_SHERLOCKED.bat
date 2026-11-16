@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1" %*
set "SHERLOCKED_EXIT=%ERRORLEVEL%"
if not "%SHERLOCKED_EXIT%"=="0" (
  echo.
  echo Setup failed. Read the error above and docs\WINDOWS_SETUP_AND_PORTABILITY.md.
  if not "%SHERLOCKED_NO_PAUSE%"=="1" pause
)
exit /b %SHERLOCKED_EXIT%
