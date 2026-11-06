from __future__ import annotations

import sys


MINIMUM_PYTHON = (3, 11)


def is_supported_python(version: tuple[int, int]) -> bool:
    return version >= MINIMUM_PYTHON


def main() -> int:
    current = (sys.version_info.major, sys.version_info.minor)
    if not is_supported_python(current):
        print(
            f"Python {MINIMUM_PYTHON[0]}.{MINIMUM_PYTHON[1]} or newer is required; "
            f"found {current[0]}.{current[1]}.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
