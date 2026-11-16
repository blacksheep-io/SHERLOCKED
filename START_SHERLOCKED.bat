@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1" %*
set "SHERLOCKED_EXIT=%ERRORLEVEL%"
if not "%SHERLOCKED_EXIT%"=="0" (
  echo.
  echo Startup failed. Run SETUP_SHERLOCKED.bat and read the error above.
  if not "%SHERLOCKED_NO_PAUSE%"=="1" pause
)
exit /b %SHERLOCKED_EXIT%
