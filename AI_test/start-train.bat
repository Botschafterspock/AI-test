@echo off
setlocal
cd /d "%~dp0"
del /q "%~dp0python\STOP_TRAINING" 2>nul
set "VENV_PYTHON=%~dp0..\.venv\Scripts\python.exe"
if exist "%VENV_PYTHON%" (
	powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0run-training.ps1" -PythonCommand "%VENV_PYTHON%"
) else (
	powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0run-training.ps1" -PythonCommand "py"
)
pause
