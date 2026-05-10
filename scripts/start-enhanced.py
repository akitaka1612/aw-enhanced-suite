#!/usr/bin/env python3
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "enhanced"))

from runtime import check_url, detached_popen, ensure_activitywatch_base_running, load_env_file, venv_python  # noqa: E402


def main() -> int:
    load_env_file(ROOT)
    host = os.environ.get("AW_ENHANCED_HOST", "127.0.0.1")
    port = os.environ.get("AW_ENHANCED_PORT", "8712")
    base_url = os.environ.get("AW_BASE_URL", "http://127.0.0.1:5600")
    reports_dir = os.environ.get("AW_REPORTS_DIR", str(Path.home() / "ActivityWatchReports"))
    helper = Path(os.environ.get("AW_BASE_HELPER", str(ROOT / "scripts" / "ensure-base-activitywatch.sh"))).expanduser()

    ensure_activitywatch_base_running(base_url, helper, ROOT)

    health_url = f"http://{host}:{port}/health"
    if not check_url(health_url):
        python_bin = venv_python(ROOT)
        if not python_bin.exists():
            print(f"Virtualenv chưa sẵn sàng. Hãy chạy: {ROOT / 'scripts' / 'install.py'}", file=sys.stderr)
            return 1
        env = os.environ.copy()
        env.update(
            {
                "AW_BASE_URL": base_url,
                "AW_REPORTS_DIR": reports_dir,
                "AW_BASE_HELPER": str(helper),
                "AW_ENHANCED_HOST": host,
                "AW_ENHANCED_PORT": port,
            }
        )
        detached_popen([str(python_bin), str(ROOT / "enhanced" / "server.py")], cwd=ROOT, env=env)

    for _ in range(20):
        if check_url(health_url):
            print(f"http://{host}:{port}")
            return 0
        import time

        time.sleep(1)

    print("Enhanced dashboard did not become ready.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
