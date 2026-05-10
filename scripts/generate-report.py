#!/usr/bin/env python3
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VENV_PYTHON = ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")

if VENV_PYTHON.exists() and Path(sys.executable).resolve() != VENV_PYTHON.resolve():
    raise SystemExit(subprocess.call([str(VENV_PYTHON), __file__, *sys.argv[1:]]))

sys.path.insert(0, str(ROOT / "enhanced"))
from core import copy_clipboard, ensure_aw_running, write_report_bundle  # noqa: E402
from runtime import load_env_file, open_path  # noqa: E402


def main() -> int:
    load_env_file(ROOT)
    ensure_aw_running()
    bundle = write_report_bundle(os.environ.get("AW_REPORT_DATE") or None)
    image_path = bundle["image_path"]
    copied = copy_clipboard(bundle["copy_ready"])
    if os.environ.get("AW_OPEN_REPORT", "1") == "1":
        open_path(Path(image_path))
    print(image_path)
    if copied:
        print("Clipboard summary copied.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
