@echo off
setlocal
cd /d "%~dp0\.."

echo Checking LIVE POOKALAM updates from the configured GitHub remote...
git rev-parse --is-inside-work-tree >nul 2>&1 || (
  echo This update check must be run from a Git clone of LIVE POOKALAM.
  exit /b 1
)

git fetch --quiet origin || exit /b 1

for /f %%A in ('git rev-parse HEAD') do set LOCAL_SHA=%%A
for /f %%A in ('git rev-parse origin/main') do set REMOTE_SHA=%%A

if "%LOCAL_SHA%"=="%REMOTE_SHA%" (
  echo LIVE POOKALAM is up to date.
  exit /b 0
)

git merge-base --is-ancestor HEAD origin/main >nul 2>&1
if %errorlevel%==0 (
  echo Update available.
  echo Run tools\update_windows.bat after the show is stopped.
  exit /b 10
)

echo Local and remote histories have diverged. Automatic update is not safe.
echo Review the Git history and resolve the divergence manually.
exit /b 2
