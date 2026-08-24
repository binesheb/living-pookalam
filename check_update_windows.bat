@echo off
setlocal

cd /d "%~dp0"

git rev-parse --is-inside-work-tree >nul 2>&1
if errorlevel 1 (
    echo This folder is not a Git working tree. Manual update is not available.
    exit /b 1
)

git remote get-url origin >nul 2>&1
if errorlevel 1 (
    echo No origin remote is configured. Cannot check for updates.
    exit /b 1
)

echo Checking origin/main for updates...
git fetch --quiet origin main
if errorlevel 1 (
    echo Unable to contact origin/main.
    exit /b 1
)

for /f %%A in ('git rev-list --count HEAD..origin/main') do set AHEAD=%%A
for /f %%A in ('git rev-list --count origin/main..HEAD') do set BEHIND=%%A

if "%AHEAD%"=="0" if "%BEHIND%"=="0" (
    echo Living Pookalam is up to date with origin/main.
    exit /b 0
)

if not "%AHEAD%"=="0" if "%BEHIND%"=="0" (
    echo Update available: %AHEAD% commit(s) ahead on origin/main.
    echo Run the documented manual update process when the projection system is idle.
    exit /b 0
)

if "%AHEAD%"=="0" if not "%BEHIND%"=="0" (
    echo Local checkout is %BEHIND% commit(s) ahead of origin/main.
    echo No automatic action was taken.
    exit /b 0
)

echo Local and origin/main have diverged.
echo No automatic action was taken; review the Git history before updating.
exit /b 0
