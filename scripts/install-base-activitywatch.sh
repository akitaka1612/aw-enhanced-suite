#!/usr/bin/env bash
set -euo pipefail

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "This installer currently downloads the official Linux ActivityWatch bundle only." >&2
  echo "On macOS/Windows, install ActivityWatch from the official GitHub releases page first." >&2
  exit 1
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[[ -f "$ROOT/.env" ]] && source "$ROOT/.env"

AW_INSTALL_DIR="${AW_INSTALL_DIR:-$HOME/.local/opt/activitywatch}"
TMP_DIR="${TMPDIR:-/tmp}/aw-enhanced-install"
mkdir -p "$TMP_DIR"

python3 - "$AW_INSTALL_DIR" "$TMP_DIR" <<'PY'
import json
import os
import platform
import shutil
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

install_dir = Path(sys.argv[1]).expanduser()
tmp_dir = Path(sys.argv[2]).expanduser()
api = "https://api.github.com/repos/ActivityWatch/activitywatch/releases/latest"
arch = platform.machine().lower()
arch_aliases = {
    "x86_64": ["x86_64", "amd64"],
    "amd64": ["x86_64", "amd64"],
    "aarch64": ["aarch64", "arm64"],
    "arm64": ["aarch64", "arm64"],
}
needles = arch_aliases.get(arch, [arch])

with urllib.request.urlopen(api, timeout=30) as resp:
    release = json.load(resp)

asset = None
for candidate in release.get("assets", []):
    name = candidate.get("name", "").lower()
    if "linux" in name and name.endswith(".zip") and any(n in name for n in needles):
        asset = candidate
        break

if not asset:
    raise SystemExit(f"Could not find a Linux zip asset for architecture: {arch}")

version = release.get("tag_name", "latest")
url = asset["browser_download_url"]
zip_path = tmp_dir / asset["name"]
extract_root = Path(tempfile.mkdtemp(prefix="aw-enhanced-extract-", dir=str(tmp_dir)))

print(f"Downloading ActivityWatch {version} from {url}")
urllib.request.urlretrieve(url, zip_path)

with zipfile.ZipFile(zip_path) as zf:
    zf.extractall(extract_root)

entries = [p for p in extract_root.iterdir() if p.name != "__MACOSX"]
source_dir = entries[0] if len(entries) == 1 and entries[0].is_dir() else extract_root

install_dir.parent.mkdir(parents=True, exist_ok=True)
backup_dir = install_dir.with_name(install_dir.name + ".bak")
if backup_dir.exists():
    shutil.rmtree(backup_dir)
if install_dir.exists():
    if backup_dir.exists():
        shutil.rmtree(backup_dir)
    install_dir.replace(backup_dir)

shutil.copytree(source_dir, install_dir, dirs_exist_ok=True)
if backup_dir.exists():
    shutil.rmtree(backup_dir)

for binary in [
    install_dir / "aw-qt",
    install_dir / "aw-server" / "aw-server",
    install_dir / "aw-server-rust" / "aw-server-rust",
    install_dir / "aw-server-rust" / "aw-sync",
    install_dir / "aw-watcher-afk" / "aw-watcher-afk",
    install_dir / "aw-watcher-input" / "aw-watcher-input",
    install_dir / "aw-watcher-window" / "aw-watcher-window",
    install_dir / "aw-notify" / "aw-notify",
]:
    if binary.exists():
        binary.chmod(0o755)

print(f"Installed ActivityWatch {version} to {install_dir}")
PY
