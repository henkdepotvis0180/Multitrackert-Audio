@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Installeer eerst de omgeving volgens README.md.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m multitrack.cli %*
