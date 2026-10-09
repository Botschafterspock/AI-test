@echo off
setlocal
cd /d "%~dp0python"
set "VENV_PYTHON=%~dp0..\.venv\Scripts\python.exe"
if exist "%VENV_PYTHON%" (
  "%VENV_PYTHON%" server_smart.py
) else (
  py server_smart.py
)
if errorlevel 1 (
  echo.
  echo Der Smart-Server konnte nicht gestartet werden. Pruefe Python und den belegten Port 8080.
  pause
)
