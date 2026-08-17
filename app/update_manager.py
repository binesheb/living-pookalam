"""Safe self-update/restart helper for the Windows Live Pookalam installation."""
from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
VENV_PYTHON = os.path.join(ROOT, ".venv", "Scripts", "python.exe")


@dataclass
class UpdateResult:
    ok: bool
    message: str
    changed: bool = False


def _run(command: list[str]) -> tuple[int, str]:
    proc = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    output = (proc.stdout + "\n" + proc.stderr).strip()
    return proc.returncode, output


def update_repository() -> UpdateResult:
    """Fetch and fast-forward the local checkout from origin/main."""
    code, output = _run(["git", "fetch", "origin", "main"])
    if code != 0:
        return UpdateResult(False, f"Git fetch failed.\n\n{output[-2500:]}")

    before_code, before = _run(["git", "rev-parse", "HEAD"])
    if before_code != 0:
        return UpdateResult(False, f"Could not read current version.\n\n{before[-1500:]}")

    code, output = _run(["git", "merge", "--ff-only", "origin/main"])
    if code != 0:
        return UpdateResult(
            False,
            "Update was not applied safely. The local checkout was not forcibly overwritten.\n\n"
            + output[-2500:],
        )

    after_code, after = _run(["git", "rev-parse", "HEAD"])
    if after_code != 0:
        return UpdateResult(False, f"Could not verify updated version.\n\n{after[-1500:]}")

    changed = before.strip() != after.strip()

    # Keep the runtime environment aligned with the checked-in product dependencies.
    python = VENV_PYTHON if os.path.exists(VENV_PYTHON) else sys.executable
    code, output = _run([python, "-m", "pip", "install", "-r", "requirements.txt"])
    if code != 0:
        return UpdateResult(
            False,
            "Code update succeeded, but dependency installation failed.\n\n"
            + output[-2500:],
            changed=changed,
        )

    version = after.strip()[:12]
    return UpdateResult(True, f"Updated successfully. Version: {version}", changed=changed)


def restart_application() -> None:
    """Replace the current process with the normal Windows launcher."""
    launcher = os.path.join(ROOT, "run_windows.bat")
    if not os.path.exists(launcher):
        raise FileNotFoundError(launcher)

    # Start the launcher detached, then let this GUI process exit naturally.
    subprocess.Popen(
        ["cmd.exe", "/c", launcher],
        cwd=ROOT,
        creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        | getattr(subprocess, "DETACHED_PROCESS", 0),
        close_fds=True,
    )


def update_and_restart() -> UpdateResult:
    result = update_repository()
    if not result.ok:
        return result
    try:
        restart_application()
    except Exception as exc:  # pragma: no cover - Windows process behavior
        return UpdateResult(False, f"Update completed, but restart failed:\n\n{exc}", result.changed)
    return UpdateResult(True, result.message + "\n\nRestarting Live Pookalam…", result.changed)
