#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[[ -f "$ROOT/.env" ]] && source "$ROOT/.env"

AW_INSTALL_DIR="${AW_INSTALL_DIR:-$HOME/.local/opt/activitywatch}"
AW_BASE_URL="${AW_BASE_URL:-http://127.0.0.1:5600}"
LOCK_FILE="${XDG_RUNTIME_DIR:-/tmp}/aw-enhanced-base.lock"
HEALTH_URL="$AW_BASE_URL/api/0/buckets/"
AW_QT="$AW_INSTALL_DIR/aw-qt"

mkdir -p "$(dirname "$LOCK_FILE")"
exec 9>"$LOCK_FILE"
flock 9

rm -f "$HOME/.cache/activitywatch/client_locks/aw-watcher-afk-at-127.0.0.1-on-5600" \
      "$HOME/.cache/activitywatch/client_locks/aw-watcher-window-at-127.0.0.1-on-5600"

if curl -fsS "$HEALTH_URL" >/dev/null 2>&1; then
  exit 0
fi

if [[ ! -x "$AW_QT" ]]; then
  echo "ActivityWatch base is not installed at: $AW_QT" >&2
  echo "Run: $ROOT/scripts/install-base-activitywatch.sh" >&2
  exit 1
fi

if ! pgrep -f "$AW_QT" >/dev/null 2>&1; then
  (
    cd "$AW_INSTALL_DIR"
    nohup "$AW_QT" 9>&- >/tmp/aw-enhanced-aw-qt.log 2>&1 &
  )
fi

deadline=$((SECONDS + 25))
until curl -fsS "$HEALTH_URL" >/dev/null 2>&1; do
  if (( SECONDS >= deadline )); then
    echo "ActivityWatch base did not become ready in time." >&2
    exit 1
  fi
  sleep 1
done
