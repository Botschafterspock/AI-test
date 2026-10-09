@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

set "MVN_CMD=mvn"
where mvn >nul 2>nul
if errorlevel 1 (
  for /f "delims=" %%M in ('dir /b /s "%USERPROFILE%\.m2\wrapper\dists\apache-maven-*\*\apache-maven-*\bin\mvn.cmd" 2^>nul') do set "MVN_CMD=%%M"
  if "%MVN_CMD%"=="mvn" (
    echo Maven wurde nicht gefunden. Installiere Maven und pruefe, dass "mvn" im PATH liegt.
    echo Fuer JavaFX wird ausserdem JDK 17 oder neuer benoetigt.
    pause
    exit /b 1
  )
)

call "%MVN_CMD%" -Pgui javafx:run
if errorlevel 1 (
  echo.
  echo Der GUI-Client konnte nicht gestartet werden. Pruefe JDK 17+, Maven und die JavaFX-Abhaengigkeiten.
  pause
  exit /b 1
)
