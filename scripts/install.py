#!/usr/bin/env python3
import os
import platform
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "enhanced"))

from runtime import current_platform, load_env_file, python_launcher, venv_python  # noqa: E402


def run(cmd: list[str], **kwargs) -> None:
    subprocess.run(cmd, check=True, **kwargs)


def install_venv() -> Path:
    venv = ROOT / ".venv"
    python = os.environ.get("PYTHON", sys.executable or "python3")
    run([python, "-m", "venv", str(venv)])
    python_bin = venv_python(ROOT)
    run([str(python_bin), "-m", "pip", "install", "--upgrade", "pip"], stdout=subprocess.DEVNULL)
    run([str(python_bin), "-m", "pip", "install", "-r", str(ROOT / "requirements.txt")])
    return python_bin


def install_linux_shortcuts() -> None:
    local_bin = Path.home() / ".local" / "bin"
    local_bin.mkdir(parents=True, exist_ok=True)
    links = {
        "awx-dashboard": ROOT / "scripts" / "open-dashboard.sh",
        "awx-report": ROOT / "scripts" / "generate-report.sh",
        "awx-start": ROOT / "scripts" / "start-enhanced.sh",
    }
    for name, target in links.items():
        link = local_bin / name
        if link.exists() or link.is_symlink():
            link.unlink()
        link.symlink_to(target)


def install_linux_autostart() -> None:
    autostart = Path.home() / ".config" / "autostart"
    autostart.mkdir(parents=True, exist_ok=True)
    desktop = autostart / "aw-enhanced-suite.desktop"
    desktop.write_text(
        "\n".join(
            [
                "[Desktop Entry]",
                "Type=Application",
                "Name=AW Enhanced Suite",
                "Comment=Start the enhanced dashboard that layers on top of ActivityWatch",
                f"Exec={ROOT / 'scripts' / 'autostart.sh'}",
                "Terminal=false",
                "X-GNOME-Autostart-enabled=true",
                "",
            ]
        ),
        encoding="utf-8",
    )


def maybe_install_base(system_name: str) -> None:
    if "--skip-base" in sys.argv[1:]:
        return
    if system_name == "linux":
        run([str(ROOT / "scripts" / "install-base-activitywatch.sh")])
        return
    print("")
    if system_name == "darwin":
        print("macOS: hãy cài ActivityWatch chính thức (.dmg) trước, rồi mở app ít nhất một lần.")
    elif system_name == "windows":
        print("Windows: hãy cài ActivityWatch chính thức (.exe installer) trước, rồi mở app ít nhất một lần.")
    print("Official releases: https://github.com/ActivityWatch/activitywatch/releases")


def main() -> int:
    load_env_file(ROOT)
    system_name = current_platform()
    install_autostart = "--autostart" in sys.argv[1:]

    install_venv()

    if system_name == "linux":
        install_linux_shortcuts()
        if install_autostart:
            install_linux_autostart()

    maybe_install_base(system_name)

    print("")
    print("Done.")
    print(f"- Open dashboard: {python_launcher()} {ROOT / 'scripts' / 'open-dashboard.py'}")
    print(f"- Generate image report: {python_launcher()} {ROOT / 'scripts' / 'generate-report.py'}")
    if system_name == "linux":
        print("- Global shortcuts installed: awx-dashboard / awx-report / awx-start")
    else:
        print("- Windows/macOS wrappers are in scripts/ (*.cmd on Windows, *.sh on macOS/Linux).")
    print(f"- Detected platform: {platform.system()} {platform.machine()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
