#!/usr/bin/env python3
import os
import platform
import shutil
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path
from typing import Optional


def load_env_file(project_root: Path) -> None:
    env_path = project_root / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key.strip(), os.path.expandvars(value))


def current_platform() -> str:
    return platform.system().lower()


def check_url(url: str, timeout: int = 5) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout):
            return True
    except Exception:
        return False


def wait_for_url(url: str, seconds: int = 20) -> bool:
    deadline = time.time() + seconds
    while time.time() < deadline:
        if check_url(url):
            return True
        time.sleep(1)
    return False


def detached_popen(args: list[str], cwd: Optional[Path] = None, env: Optional[dict] = None) -> subprocess.Popen:
    kwargs = {
        "cwd": str(cwd) if cwd else None,
        "env": env,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }
    system = current_platform()
    if system == "windows":
        flags = 0
        flags |= getattr(subprocess, "DETACHED_PROCESS", 0)
        flags |= getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        return subprocess.Popen(args, creationflags=flags, **kwargs)
    return subprocess.Popen(args, start_new_session=True, **kwargs)


def candidate_linux_aw_qt(project_root: Path) -> list[Path]:
    install_dir = Path(os.environ.get("AW_INSTALL_DIR", str(Path.home() / ".local/opt/activitywatch"))).expanduser()
    return [
        install_dir / "aw-qt",
        Path("/opt/activitywatch/aw-qt"),
        project_root / "activitywatch" / "aw-qt",
    ]


def candidate_windows_aw_exe() -> list[Path]:
    paths: list[Path] = []
    custom = os.environ.get("AW_WINDOWS_EXE")
    if custom:
        paths.append(Path(custom).expanduser())
    for env_name in ("LOCALAPPDATA", "ProgramFiles", "ProgramFiles(x86)"):
        base = os.environ.get(env_name)
        if not base:
            continue
        root = Path(base)
        paths.extend(
            [
                root / "Programs" / "ActivityWatch" / "ActivityWatch.exe",
                root / "ActivityWatch" / "ActivityWatch.exe",
            ]
        )
    return paths


def candidate_macos_app() -> list[Path]:
    paths: list[Path] = []
    custom = os.environ.get("AW_MACOS_APP")
    if custom:
        paths.append(Path(custom).expanduser())
    paths.extend(
        [
            Path("/Applications/ActivityWatch.app"),
            Path.home() / "Applications" / "ActivityWatch.app",
        ]
    )
    return paths


def start_base_app(base_url: str, helper_path: Optional[Path], project_root: Path) -> bool:
    system = current_platform()

    if system == "linux":
        if helper_path and helper_path.exists() and os.access(helper_path, os.X_OK):
            try:
                subprocess.run(
                    [str(helper_path)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=True,
                )
                return True
            except Exception:
                pass
        for path in candidate_linux_aw_qt(project_root):
            if path.exists() and os.access(path, os.X_OK):
                detached_popen([str(path)], cwd=path.parent)
                return True
        return False

    if system == "darwin":
        for app in candidate_macos_app():
            if app.exists():
                try:
                    detached_popen(["open", str(app)])
                    return True
                except Exception:
                    continue
        try:
            detached_popen(["open", "-a", "ActivityWatch"])
            return True
        except Exception:
            return False

    if system == "windows":
        for exe in candidate_windows_aw_exe():
            if exe.exists():
                try:
                    detached_popen([str(exe)], cwd=exe.parent)
                    return True
                except Exception:
                    continue
        return False

    return False


def ensure_activitywatch_base_running(base_url: str, helper_path: Optional[Path], project_root: Path) -> None:
    health_url = f"{base_url.rstrip('/')}/api/0/buckets/"
    if check_url(health_url):
        return
    started = start_base_app(base_url, helper_path, project_root)
    if check_url(health_url):
        return
    if started and wait_for_url(health_url, seconds=25):
        return
    system = current_platform()
    if system == "linux":
        raise RuntimeError(
            "Could not start ActivityWatch base automatically. "
            "Run scripts/install-base-activitywatch.sh or start aw-qt manually."
        )
    if system == "darwin":
        raise RuntimeError(
            "Could not detect a running ActivityWatch on macOS. "
            "Please install/open the official ActivityWatch app, then try again."
        )
    if system == "windows":
        raise RuntimeError(
            "Could not detect a running ActivityWatch on Windows. "
            "Please install/open the official ActivityWatch app, then try again."
        )
    raise RuntimeError("Could not start ActivityWatch base automatically.")


def open_url(url: str) -> bool:
    try:
        return bool(webbrowser.open(url))
    except Exception:
        return False


def open_path(path: Path) -> bool:
    return open_url(path.resolve().as_uri())


def copy_text_to_clipboard(text: str) -> bool:
    system = current_platform()
    candidates: list[list[str]] = []
    if system == "darwin":
        candidates = [["pbcopy"]]
    elif system == "windows":
        candidates = [["clip"]]
    else:
        if shutil.which("xclip"):
            candidates.append(["xclip", "-selection", "clipboard"])
        if shutil.which("wl-copy"):
            candidates.append(["wl-copy"])
        if shutil.which("xsel"):
            candidates.append(["xsel", "--clipboard", "--input"])

    for command in candidates:
        try:
            subprocess.run(command, input=text.encode("utf-8"), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            return True
        except Exception:
            continue
    return False


def venv_python(project_root: Path) -> Path:
    if current_platform() == "windows":
        return project_root / ".venv" / "Scripts" / "python.exe"
    return project_root / ".venv" / "bin" / "python"


def python_launcher() -> str:
    if current_platform() == "windows":
        return "py -3"
    return sys.executable or "python3"
