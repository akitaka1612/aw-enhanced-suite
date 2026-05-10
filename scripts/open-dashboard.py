#!/usr/bin/env python3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "start-enhanced.py")],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        sys.stderr.write(result.stderr or result.stdout)
        return result.returncode
    url = (result.stdout or "").strip().splitlines()[-1]
    sys.path.insert(0, str(ROOT / "enhanced"))
    from runtime import open_url  # noqa: E402

    open_url(url)
    print(url)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
