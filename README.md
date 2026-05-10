# AW Enhanced Suite

A polished local analytics layer for **ActivityWatch** with a cleaner dashboard, richer categorization, and one-click daily report generation.

## Overview

AW Enhanced Suite sits on top of the official ActivityWatch desktop app and adds:

- a clearer, more readable dashboard
- custom activity categorization by category and subcategory
- daily comparison against the previous day and recent baseline
- **PNG daily reports**
- **Markdown daily reports**
- better browser activity summaries when `aw-watcher-web` is available

> This repository is an enhancement layer, **not a fork of ActivityWatch itself**.  
> On **Linux**, the installer can fetch the official ActivityWatch bundle automatically.  
> On **macOS** and **Windows**, users should install the official ActivityWatch app first.

## Features

- Enhanced local dashboard on top of ActivityWatch data
- Daily usage summary with productivity and focus metrics
- Category / subcategory breakdown
- Domain-aware browser activity classification
- Exportable Markdown and PNG reports
- Lightweight local HTTP service
- Cross-platform launch flow for Linux, macOS, and Windows

## Platform Support

| Platform | Status | Notes |
|---|---|---|
| Linux | Recommended | Best-supported path; installer can download ActivityWatch automatically |
| macOS | Supported | Install the official ActivityWatch `.dmg` first |
| Windows | Supported | Install the official ActivityWatch `.exe` first |

## Architecture

This project works as a local layer above the official ActivityWatch app:

1. **ActivityWatch base app** collects activity data and serves it on `http://127.0.0.1:5600`
2. **AW Enhanced Suite** reads that live data, enriches it, and serves an enhanced dashboard
3. Reports are generated locally as **Markdown** and **PNG**

Default enhanced dashboard address:

```text
http://127.0.0.1:8712
```

## Quick Start

### Linux

```bash
git clone https://github.com/akitaka1612/aw-enhanced-suite.git
cd aw-enhanced-suite
./scripts/install.sh
./scripts/open-dashboard.sh
```

Generate a report:

```bash
./scripts/generate-report.sh
```

Optional Linux shortcuts installed by the setup script:

```bash
awx-dashboard
awx-report
awx-start
```

### macOS

1. Install the official ActivityWatch app from GitHub releases
2. Open ActivityWatch at least once
3. Run:

```bash
git clone https://github.com/akitaka1612/aw-enhanced-suite.git
cd aw-enhanced-suite
python3 scripts/install.py --skip-base
python3 scripts/open-dashboard.py
```

Generate a report:

```bash
python3 scripts/generate-report.py
```

### Windows

1. Install the official ActivityWatch app from GitHub releases
2. Launch ActivityWatch at least once
3. In PowerShell or Command Prompt:

```powershell
git clone https://github.com/akitaka1612/aw-enhanced-suite.git
cd aw-enhanced-suite
py -3 scripts\install.py --skip-base
py -3 scripts\open-dashboard.py
```

Generate a report:

```powershell
py -3 scripts\generate-report.py
```

## Repository Structure

```text
enhanced/      Core Python logic, HTTP server, UI assets, rules
scripts/       Installers, launchers, report commands
autostart/     Desktop autostart templates
systemd/       Example systemd unit
```

Key files:

- `enhanced/core.py` — summarization, categorization, reporting
- `enhanced/server.py` — local HTTP server for the enhanced dashboard
- `enhanced/runtime.py` — cross-platform runtime helpers
- `scripts/install.py` — cross-platform installer for the enhanced layer
- `scripts/install-base-activitywatch.sh` — Linux-only installer for official ActivityWatch
- `scripts/open-dashboard.py` — starts dependencies and opens the dashboard
- `scripts/generate-report.py` — creates Markdown + PNG reports

## Requirements

### Common

- Git
- Python 3.10+
- Official ActivityWatch base app

### Platform-specific

- **Linux:** `curl`, plus one clipboard tool such as `xclip`, `wl-copy`, or `xsel`
- **macOS:** `pbcopy` is used when available
- **Windows:** `clip.exe` is used when available

## Output and Storage

By default:

- ActivityWatch data stays in the normal ActivityWatch data directory
- Linux ActivityWatch bundle installs to:

```text
~/.local/opt/activitywatch
```

- Generated reports are written to:

```text
~/ActivityWatchReports
```

## Browser Watcher

For richer web activity summaries, install the official `aw-watcher-web` browser extension.

Without the extension, the dashboard still works, but browser-related domain and tab-level reporting will be less detailed.

## Autostart

### Linux

```bash
./scripts/install.sh --autostart
```

This installs an XDG autostart entry under `~/.config/autostart/`.

### macOS

Add ActivityWatch and/or the launcher script to **Login Items**.

### Windows

Add the launcher to **Startup** or create a **Task Scheduler** entry.

## Configuration

Copy `.env.example` to `.env` and adjust values if needed:

```bash
cp .env.example .env
```

Useful variables:

- `AW_INSTALL_DIR`
- `AW_BASE_URL`
- `AW_ENHANCED_HOST`
- `AW_ENHANCED_PORT`
- `AW_REPORTS_DIR`
- `AW_MACOS_APP`
- `AW_WINDOWS_EXE`

## Notes

- The enhanced dashboard reads **live local data** from the base ActivityWatch service on port `5600`
- The enhanced dashboard serves its UI on port `8712` by default
- Everything runs locally; this project does **not** upload user activity data anywhere

## Related Links

- ActivityWatch documentation: https://docs.activitywatch.net/en/latest/getting-started.html
- ActivityWatch releases: https://github.com/ActivityWatch/activitywatch/releases

## License and Third-Party Components

See:

- `THIRD_PARTY_NOTICES.md`

