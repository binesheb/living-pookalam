@echo off
setlocal
cd /d "%~dp0"
echo Checking for updates...
git pull --ff-only
if errorlevel 1 echo Git update skipped or failed. Starting current version.
if not exist .venv python -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
python launcher.py
pause
