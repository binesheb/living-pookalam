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

echo Checking for local changes before update...
git status --porcelain --untracked-files=all | findstr . >nul
if not errorlevel 1 goto local_changes

echo Checking for updates...
git fetch origin
if errorlevel 1 goto deps
git pull --ff-only
if not errorlevel 1 goto deps

echo Normal update failed. Keeping current version.
goto deps

:local_changes
echo Local changes detected. Automatic update was skipped to preserve local work.
echo Review the working tree and use the documented manual update process when ready.
goto deps

:repair
echo Unfinished Git operation detected.
echo Automatic recovery was skipped to avoid overwriting local work.
echo Resolve or abort the Git operation manually, then run the application again.
goto deps

:deps
if not exist .venv python -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python launcher.py
pause
