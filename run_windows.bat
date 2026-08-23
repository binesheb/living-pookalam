@echo off
setlocal
cd /d "%~dp0"

echo Checking repository state...
git rev-parse --is-inside-work-tree >nul 2>&1
if errorlevel 1 goto deps

echo Checking for unfinished Git operations...
git diff --name-only --diff-filter=U | findstr . >nul
if not errorlevel 1 goto repair
if exist .git\MERGE_HEAD goto repair
if exist .git\rebase-merge goto repair
if exist .git\rebase-apply goto repair
if exist .git\CHERRY_PICK_HEAD goto repair

echo Checking for updates...
git fetch origin
if errorlevel 1 goto deps
git pull --ff-only
if not errorlevel 1 goto deps

echo Normal update failed. Keeping current version.
goto deps

:repair
echo Repairing unfinished Git state from GitHub main...
git merge --abort >nul 2>&1
git rebase --abort >nul 2>&1
git cherry-pick --abort >nul 2>&1
git fetch origin
if errorlevel 1 goto deps
git reset --hard origin/main
if errorlevel 1 goto deps
git clean -fd

git status --short

:deps
if not exist .venv python -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
python launcher.py
pause
