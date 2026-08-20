@echo off
cd /d "%~dp0"
where bash >nul 2>&1
if errorlevel 1 (
  echo Git Bash or WSL is required to run this launcher.
  echo Install Git for Windows: https://git-scm.com/download/win
  pause
  exit /b 1
)
bash scripts/start-local.sh
pause
