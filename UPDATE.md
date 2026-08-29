# Updating Living Pookalam

Living Pookalam is a Windows projector/camera application. Update it only when the projection system is idle and no calibration or local changes need to be preserved.

## Safe manual update

1. Stop the application and close the projector/camera windows.
2. Open a Command Prompt in the repository folder.
3. Check the working tree:

```bat
git status --short
```

If anything is listed, review or commit/stash it before updating. Do not discard calibration or other local work automatically.

4. Fetch and fast-forward only:

```bat
git fetch origin main
git pull --ff-only origin main
```

5. Start the application normally:

```bat
run_windows.bat
```

The startup script creates/uses `.venv` and installs the dependencies listed in `requirements.txt`.

## Automatic startup behavior

`run_windows.bat` checks `origin/main` and attempts a fast-forward update only. If Git reports a conflict, divergence, or an unfinished operation, the script keeps the current checkout and does not attempt destructive recovery.

Use `check_update_windows.bat` when you want a read-only update check without changing the checkout.

## Rollback

If a newly updated revision is not suitable, first identify a previously known-good commit:

```bat
git log --oneline -10
```

Then create a recovery branch before switching revisions:

```bat
git branch recovery-before-rollback
git checkout <known-good-commit>
```

Run and validate the application. Once the known-good revision is confirmed, return to `main` and resolve the update deliberately rather than forcing the startup updater to overwrite history.
