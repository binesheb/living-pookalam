@echo off
setlocal
cd /d "%~dp0"
echo Checking for updates...
git pull --ff-only
if errorlevel 1 (
  echo Update failed. Check your Git connection and try again.
  pause
  exit /b 1
)
if not exist .venv (
  py -3 -m venv .venv || python -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
python main.py
pause
