@echo off
setlocal
cd /d "%~dp0\.."

echo Updating LIVE POOKALAM from the configured GitHub remote...
git rev-parse --is-inside-work-tree >nul 2>&1 || (
  echo This updater must be run from a Git clone of LIVE POOKALAM.
  exit /b 1
)

git status --porcelain | findstr . >nul && (
  echo Local changes detected. Update stopped to avoid overwriting your work.
  echo Commit or stash your changes, then run this updater again.
  exit /b 2
)

git fetch --tags origin || exit /b 1
git pull --ff-only origin main || exit /b 1

if not exist .venv\Scripts\python.exe (
  py -3 -m venv .venv || exit /b 1
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt || exit /b 1

echo Update complete.
