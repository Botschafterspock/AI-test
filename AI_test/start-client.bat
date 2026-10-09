@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist bin mkdir bin
javac -encoding UTF-8 -d bin src\main\java\de\jojo\ai\ChatClient.java
if errorlevel 1 (
  echo Fehler beim Kompilieren. Ist ein JDK installiert? Pruefe mit: javac -version
  pause
  exit /b 1
)
java -cp bin de.jojo.ai.ChatClient
pause