param(
    [switch]$CheckOnly
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw 'Git is required to update LIVE POOKALAM.'
}

$status = git status --porcelain
if ($status) {
    throw 'Local changes detected. Commit or stash them before updating.'
}

git fetch origin main
$local = (git rev-parse HEAD).Trim()
$remote = (git rev-parse origin/main).Trim()

if ($local -eq $remote) {
    Write-Host 'LIVE POOKALAM is already up to date.'
    exit 0
}

if ($CheckOnly) {
    Write-Host "Update available: $($remote.Substring(0,12))"
    exit 10
}

git merge --ff-only origin/main
if (Test-Path 'requirements.txt') {
    $python = Join-Path $root '.venv\Scripts\python.exe'
    if (-not (Test-Path $python)) { $python = (Get-Command python).Source }
    & $python -m pip install -r requirements.txt
}

Write-Host "LIVE POOKALAM updated to $((git rev-parse HEAD).Substring(0,12))."
