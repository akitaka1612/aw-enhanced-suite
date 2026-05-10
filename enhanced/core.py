#!/usr/bin/env python3
import json
import math
import os
import re
import subprocess
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from textwrap import fill
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib import ticker
from matplotlib.patches import FancyBboxPatch
from runtime import copy_text_to_clipboard, ensure_activitywatch_base_running


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
RULES_PATH = ROOT / "activitywatch_rules.json"
BASE_URL = os.environ.get("AW_BASE_URL", "http://127.0.0.1:5600")
AW_BASE_HELPER = Path(
    os.environ.get(
        "AW_BASE_HELPER",
        str(PROJECT_ROOT / "scripts" / "ensure-base-activitywatch.sh"),
    )
).expanduser()
REPORTS_DIR = Path(
    os.environ.get("AW_REPORTS_DIR", str(Path.home() / "ActivityWatchReports"))
).expanduser()
SERVER_PORT = int(os.environ.get("AW_ENHANCED_PORT", "8712"))
SERVER_URL = f"http://127.0.0.1:{SERVER_PORT}"


def parse_ts(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


def fmt_duration(seconds: float) -> str:
    total = int(round(seconds))
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    parts = []
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if secs and not hours:
        parts.append(f"{secs}s")
    return " ".join(parts) or "0m"


def fmt_delta(seconds: float) -> str:
    sign = "+" if seconds >= 0 else "-"
    return f"{sign}{fmt_duration(abs(seconds))}"


def request_json(path: str) -> object:
    with urllib.request.urlopen(BASE_URL + path, timeout=20) as response:
        return json.load(response)


def ensure_aw_running() -> None:
    ensure_activitywatch_base_running(BASE_URL, AW_BASE_HELPER, PROJECT_ROOT)


def load_rules() -> dict:
    data = json.loads(RULES_PATH.read_text(encoding="utf-8"))
    for rule in data["rules"]:
        rule["_app_patterns"] = [re.compile(pattern, re.I) for pattern in rule.get("app_regex", [])]
        rule["_title_patterns"] = [re.compile(pattern, re.I) for pattern in rule.get("title_regex", [])]
        rule["_domain_patterns"] = [re.compile(pattern, re.I) for pattern in rule.get("domain_regex", [])]
    for rule in data.get("domain_rules", []):
        rule["_domain_patterns"] = [re.compile(pattern, re.I) for pattern in rule.get("domain_regex", [])]
        rule["_title_patterns"] = [re.compile(pattern, re.I) for pattern in rule.get("title_regex", [])]
    return data


def choose_bucket(bucket_ids: List[str], prefix: str) -> Optional[str]:
    for bucket_id in bucket_ids:
        if bucket_id.startswith(prefix):
            return bucket_id
    return None


def choose_buckets(bucket_ids: List[str], prefix: str) -> List[str]:
    return [bucket_id for bucket_id in bucket_ids if bucket_id.startswith(prefix)]


def fetch_events(bucket_id: str, start_utc: datetime, end_utc: datetime) -> List[dict]:
    params = urllib.parse.urlencode({"start": start_utc.isoformat(), "end": end_utc.isoformat()})
    return request_json(
        f"/api/0/buckets/{urllib.parse.quote(bucket_id, safe='')}/events?{params}"
    )


def local_day_bounds(date_str: Optional[str] = None) -> Tuple[datetime, datetime]:
    local_now = datetime.now().astimezone()
    if date_str:
        day = datetime.strptime(date_str, "%Y-%m-%d").date()
        start = datetime(day.year, day.month, day.day, tzinfo=local_now.tzinfo)
    else:
        start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
    return start, start + timedelta(days=1)


def active_intervals(events: List[dict]) -> List[Tuple[datetime, datetime]]:
    intervals: List[Tuple[datetime, datetime]] = []
    for event in events:
        if event.get("data", {}).get("status") != "not-afk":
            continue
        start = parse_ts(event["timestamp"])
        end = start + timedelta(seconds=float(event.get("duration", 0)))
        if end > start:
            intervals.append((start, end))
    intervals.sort(key=lambda item: item[0])
    return intervals


def clean_title(title: str, app: str, rules: dict) -> str:
    value = " ".join((title or "").split())
    for suffix in rules.get("browser_suffixes", []):
        if value.endswith(suffix):
            value = value[: -len(suffix)].rstrip(" -")
            break
    if value in {"", "unknown"}:
        return app or "Unknown"
    return value


def normalize_activity(app: str, title: str, rules: dict) -> str:
    terminal_apps = {item.lower() for item in rules.get("terminal_apps", [])}
    if app.lower() in terminal_apps or "terminal" in app.lower():
        return "Terminal session"
    return clean_title(title, app, rules)


def normalize_domain(url: str) -> Optional[str]:
    try:
        hostname = urlparse(url).hostname or ""
    except Exception:
        return None
    hostname = hostname.lower()
    if hostname.startswith("www."):
        hostname = hostname[4:]
    return hostname or None


def normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (value or "").lower())


def app_matches(app: str, values: List[str]) -> bool:
    app_key = normalize_key(app)
    return any(normalize_key(value) == app_key for value in values)


def format_web_activity(url: Optional[str], title: str, app: str, rules: dict) -> str:
    domain = normalize_domain(url) if url else None
    clean = clean_title(title, app, rules)
    if domain and clean and clean.lower() != domain.lower():
        return f"{domain} — {clean}"
    if domain:
        return domain
    return clean


def classify(app: str, title: str, activity: str, rules: dict, domain: Optional[str] = None, url: Optional[str] = None) -> dict:
    app_lc = app.lower()
    title_lc = title.lower()
    activity_lc = activity.lower()
    domain_lc = (domain or "").lower()

    for rule in rules.get("domain_rules", []):
        domain_match = any(pattern.search(domain_lc) for pattern in rule["_domain_patterns"])
        title_match = any(pattern.search(title_lc) or pattern.search(activity_lc) for pattern in rule["_title_patterns"])
        if rule.get("match") == "all":
            matched = (
                (not rule["_domain_patterns"] or domain_match)
                and (not rule["_title_patterns"] or title_match)
                and (rule["_domain_patterns"] or rule["_title_patterns"])
            )
        else:
            matched = (rule["_domain_patterns"] or rule["_title_patterns"]) and (domain_match or title_match)
        if matched:
            return {
                "category": rule["category"],
                "subcategory": rule["subcategory"],
                "color": rule["color"],
                "productive": bool(rule.get("productive", False)),
                "deep_work": bool(rule.get("deep_work", False)),
            }

    for rule in rules["rules"]:
        app_match = any(pattern.search(app_lc) for pattern in rule["_app_patterns"])
        title_match = any(
            pattern.search(title_lc) or pattern.search(activity_lc) for pattern in rule["_title_patterns"]
        )
        if (rule["_app_patterns"] or rule["_title_patterns"]) and (app_match or title_match):
            return {
                "category": rule["category"],
                "subcategory": rule["subcategory"],
                "color": rule["color"],
                "productive": bool(rule.get("productive", False)),
                "deep_work": bool(rule.get("deep_work", False)),
            }

    if app_matches(app, rules.get("reader_apps", [])):
        return {"category": "Learning", "subcategory": "Reading and ebooks", "color": "#2e7d32", "productive": True, "deep_work": True}
    if app_matches(app, rules.get("editor_apps", [])):
        return {"category": "Coding", "subcategory": "Code editor", "color": "#0f766e", "productive": True, "deep_work": True}
    if app_matches(app, rules.get("terminal_apps", [])) or "terminal" in app_lc:
        return {"category": "Coding", "subcategory": "Terminal", "color": "#0f766e", "productive": True, "deep_work": True}
    if app_matches(app, rules.get("chat_apps", [])):
        return {"category": "Communication", "subcategory": "Chat and messaging", "color": "#c2410c", "productive": False, "deep_work": False}
    if app_matches(app, rules.get("media_apps", [])):
        return {"category": "Entertainment", "subcategory": "Video and media", "color": "#7c3aed", "productive": False, "deep_work": False}
    if app_matches(app, rules.get("system_apps", [])) or "setting" in title_lc or "control center" in title_lc:
        return {"category": "Admin", "subcategory": "Monitoring and settings", "color": "#475569", "productive": False, "deep_work": False}
    if app_matches(app, rules.get("browser_apps", [])) or domain_lc or "browser" in app_lc:
        return {"category": "Web", "subcategory": "Browser", "color": "#2563eb", "productive": False, "deep_work": False}
    if any(token in title_lc for token in ("file manager", "files", "explorer", "downloads", "documents")):
        return {"category": "Admin", "subcategory": "File management", "color": "#475569", "productive": False, "deep_work": False}
    if any(token in title_lc for token in ("github", "gitlab", "stack overflow", "stackoverflow", "docs", "api", "developer")):
        return {"category": "Coding", "subcategory": "Reference and tooling", "color": "#0f766e", "productive": True, "deep_work": True}
    if any(token in title_lc for token in ("lesson", "lecture", "tutorial", "course", "paper", "research", "study")):
        return {"category": "Learning", "subcategory": "Reference and study", "color": "#2e7d32", "productive": True, "deep_work": True}
    return {"category": "General", "subcategory": "Miscellaneous activity", "color": "#6b7280", "productive": False, "deep_work": False}


def build_segments(window_events: List[dict], not_afk: List[Tuple[datetime, datetime]], rules: dict) -> List[dict]:
    return build_segments_with_web(window_events, [], not_afk, rules)


def build_segments_with_web(
    window_events: List[dict],
    web_events: List[dict],
    not_afk: List[Tuple[datetime, datetime]],
    rules: dict,
) -> List[dict]:
    segments: List[dict] = []
    afk_index = 0
    web_contexts = []
    for event in sorted(web_events, key=lambda item: parse_ts(item["timestamp"])):
        start = parse_ts(event["timestamp"])
        end = start + timedelta(seconds=float(event.get("duration", 0)))
        data = event.get("data", {})
        if end <= start:
            continue
        web_contexts.append(
            {
                "start": start,
                "end": end,
                "url": data.get("url"),
                "title": data.get("title") or data.get("pageTitle") or "",
                "domain": normalize_domain(data.get("url", "")) if data.get("url") else None,
            }
        )

    for event in sorted(window_events, key=lambda item: parse_ts(item["timestamp"])):
        start = parse_ts(event["timestamp"])
        end = start + timedelta(seconds=float(event.get("duration", 0)))
        if end <= start:
            continue

        data = event.get("data", {})
        app = data.get("app") or "Unknown"
        if app == "aw-qt":
            continue
        title = data.get("title") or data.get("url") or app
        url = None
        domain = None
        if app_matches(app, rules.get("browser_apps", [])) or "browser" in app.lower():
            best_context = None
            best_overlap = 0.0
            for context in web_contexts:
                if context["end"] <= start:
                    continue
                if context["start"] >= end:
                    break
                overlap = (
                    min(end, context["end"]) - max(start, context["start"])
                ).total_seconds()
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_context = context
            if best_context:
                url = best_context["url"]
                domain = best_context["domain"]
                title = best_context["title"] or title
                activity = format_web_activity(url, title, app, rules)
            else:
                activity = normalize_activity(app, title, rules)
        else:
            activity = normalize_activity(app, title, rules)
        meta = classify(app, title, activity, rules, domain=domain, url=url)

        while afk_index < len(not_afk) and not_afk[afk_index][1] <= start:
            afk_index += 1

        check_index = afk_index
        while check_index < len(not_afk) and not_afk[check_index][0] < end:
            active_start = max(start, not_afk[check_index][0])
            active_end = min(end, not_afk[check_index][1])
            if active_end > active_start:
                segments.append(
                    {
                        "start": active_start,
                        "end": active_end,
                        "seconds": (active_end - active_start).total_seconds(),
                        "app": app,
                        "title": clean_title(title, app, rules),
                        "activity": activity,
                        "url": url,
                        "domain": domain,
                        **meta,
                    }
                )
            if not_afk[check_index][1] >= end:
                break
            check_index += 1
    return segments


def merge_sessions(segments: List[dict]) -> List[dict]:
    merged: List[dict] = []
    for segment in sorted(segments, key=lambda item: item["start"]):
        if not merged:
            merged.append(segment.copy())
            continue
        last = merged[-1]
        gap = (segment["start"] - last["end"]).total_seconds()
        same_context = (
            segment["category"] == last["category"]
            and segment["subcategory"] == last["subcategory"]
            and segment["app"] == last["app"]
            and segment["activity"] == last["activity"]
        )
        if same_context and gap <= 300:
            last["end"] = max(last["end"], segment["end"])
            last["seconds"] += segment["seconds"]
        else:
            merged.append(segment.copy())
    return merged


def accumulate_by_hour(segments: List[dict], start_local: datetime) -> List[dict]:
    hours = [{"hour": hour, "seconds": 0.0} for hour in range(24)]
    for segment in segments:
        cursor = segment["start"].astimezone(start_local.tzinfo)
        end = segment["end"].astimezone(start_local.tzinfo)
        while cursor < end:
            next_hour = (cursor.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1))
            chunk_end = min(end, next_hour)
            hours[cursor.hour]["seconds"] += (chunk_end - cursor).total_seconds()
            cursor = chunk_end
    return hours


def rank_map(values: Dict[str, float], limit: int = 8) -> List[dict]:
    ranked = []
    for name, seconds in sorted(values.items(), key=lambda item: item[1], reverse=True)[:limit]:
        ranked.append({"name": name, "seconds": seconds, "label": fmt_duration(seconds)})
    return ranked


def to_hours(seconds: float) -> float:
    return round(seconds / 3600.0, 2)


def shorten_label(value: str, limit: int = 42) -> str:
    value = " ".join(str(value).split())
    if len(value) <= limit:
        return value
    return value[: limit - 1].rstrip() + "..."


def style_panel(ax, title: str, subtitle: str) -> None:
    ax.set_facecolor("#ffffff")
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(colors="#52606d", labelsize=10)
    ax.grid(color="#e5e9f2", linewidth=0.8, axis="x")
    ax.set_axisbelow(True)
    ax.set_title(title, loc="left", fontsize=14, fontweight="bold", color="#182433", pad=18)
    ax.text(
        0.0,
        1.02,
        subtitle,
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=10,
        color="#667382",
    )


def render_empty_panel(ax, title: str, subtitle: str, message: str) -> None:
    style_panel(ax, title, subtitle)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.text(
        0.5,
        0.5,
        message,
        transform=ax.transAxes,
        ha="center",
        va="center",
        fontsize=12,
        color="#667382",
    )


def render_horizontal_bars(
    ax,
    title: str,
    subtitle: str,
    items: List[dict],
    *,
    colors: Optional[List[str]] = None,
    fallback: str,
) -> None:
    if not items:
        render_empty_panel(ax, title, subtitle, fallback)
        return

    style_panel(ax, title, subtitle)
    visible_items = items[:6]
    max_seconds = max((item["seconds"] for item in visible_items), default=0.0)
    if max_seconds < 3600:
        unit_label = "Minutes"
        scale = 60.0
    else:
        unit_label = "Hours"
        scale = 3600.0

    labels = [shorten_label(item["name"]) for item in visible_items][::-1]
    values = [round(item["seconds"] / scale, 2) for item in visible_items][::-1]
    palette = colors or ["#206bc4"] * len(values)
    palette = palette[: len(values)][::-1]
    bars = ax.barh(labels, values, color=palette, edgecolor="none", height=0.62)
    ax.set_xlabel(unit_label, color="#52606d")
    ax.xaxis.set_major_locator(ticker.MaxNLocator(5))
    for bar, item in zip(bars, visible_items[::-1]):
        ax.text(
            bar.get_width() + max(values) * 0.03 if max(values) else 0.05,
            bar.get_y() + bar.get_height() / 2,
            item["label"],
            va="center",
            ha="left",
            fontsize=10,
            color="#182433",
        )
    ax.margins(x=0.12)


def render_hourly_chart(ax, summary: dict) -> None:
    hours = summary["hours"]
    style_panel(ax, "Hourly activity", "Active time across the day.")
    if not hours:
        ax.text(0.5, 0.5, "No hourly data available.", transform=ax.transAxes, ha="center", va="center")
        return
    labels = [f"{item['hour']:02d}" for item in hours]
    values = [to_hours(item["seconds"]) for item in hours]
    colors = ["#206bc4" if value > 0 else "#dce6f5" for value in values]
    ax.bar(labels, values, color=colors, width=0.78)
    ax.set_xlabel("Hour", color="#52606d")
    ax.set_ylabel("Hours", color="#52606d")
    ax.yaxis.set_major_locator(ticker.MaxNLocator(5))
    max_index = max(range(len(values)), key=values.__getitem__) if any(values) else None
    if max_index is not None and values[max_index] > 0:
        ax.scatter([labels[max_index]], [values[max_index]], color="#0ca678", s=40, zorder=3)
        ax.text(
            labels[max_index],
            values[max_index] + max(values) * 0.06,
            f"Peak {values[max_index]:.1f}h",
            ha="center",
            va="bottom",
            fontsize=10,
            color="#0b7285",
        )


def render_trend_chart(ax, comparison: dict) -> None:
    daily = comparison["daily"]
    style_panel(ax, "7-day trend", "Active time, deep work, and focus ratio.")
    if not daily:
        ax.text(0.5, 0.5, "No daily trend data available.", transform=ax.transAxes, ha="center", va="center")
        return
    labels = [item["date"][5:] for item in daily]
    active = [to_hours(item["total_seconds"]) for item in daily]
    deep = [to_hours(item["deep_work_seconds"]) for item in daily]
    focus = [item["focus_ratio"] for item in daily]
    positions = list(range(len(labels)))
    width = 0.36
    ax.bar([pos - width / 2 for pos in positions], active, width=width, color="#206bc4", label="Active")
    ax.bar([pos + width / 2 for pos in positions], deep, width=width, color="#0ca678", label="Deep work")
    ax.set_xticks(positions, labels)
    ax.set_ylabel("Hours", color="#52606d")
    ax.legend(loc="upper left", frameon=False, ncols=2)
    ax.yaxis.set_major_locator(ticker.MaxNLocator(5))

    focus_ax = ax.twinx()
    for spine in focus_ax.spines.values():
        spine.set_visible(False)
    focus_ax.plot(positions, focus, color="#f59f00", linewidth=2.2, marker="o")
    focus_ax.set_ylim(0, max(100, math.ceil(max(focus) / 10.0) * 10 if focus else 100))
    focus_ax.set_ylabel("Focus %", color="#f59f00")
    focus_ax.tick_params(colors="#f59f00", labelsize=10)
    focus_ax.grid(False)


def render_header(ax, summary: dict, comparison: dict) -> None:
    ax.set_facecolor("#f5f7fb")
    ax.axis("off")
    ax.text(
        0.0,
        0.96,
        "ActivityWatch Daily Usage Report",
        fontsize=24,
        fontweight="bold",
        color="#182433",
        ha="left",
        va="top",
        transform=ax.transAxes,
    )
    ax.text(
        0.0,
        0.84,
        f"Date: {summary['date']}    Generated: {summary['generated_at']}",
        fontsize=11,
        color="#52606d",
        ha="left",
        va="top",
        transform=ax.transAxes,
    )
    ax.text(
        0.0,
        0.77,
        "Source: Original ActivityWatch buckets + browser watcher URL events",
        fontsize=11,
        color="#52606d",
        ha="left",
        va="top",
        transform=ax.transAxes,
    )

    cards = [
        ("Total active", summary["total_label"], f"{summary['context_switches']} context switches", "#206bc4"),
        ("Deep work", summary["deep_work_label"], f"{summary['focus_ratio']}% focus ratio", "#0ca678"),
        ("Productive time", summary["productive_label"], f"{len(summary['categories'])} category groups", "#f59f00"),
        ("Longest session", summary["longest_session_label"], "Longest continuous block", "#d6336c"),
    ]
    x_positions = [0.00, 0.255, 0.51, 0.765]
    for x_pos, (title, value, subtitle, accent) in zip(x_positions, cards):
        patch = FancyBboxPatch(
            (x_pos, 0.06),
            0.22,
            0.52,
            boxstyle="round,pad=0.012,rounding_size=0.03",
            linewidth=1,
            edgecolor="#dce3ee",
            facecolor="#ffffff",
            transform=ax.transAxes,
        )
        ax.add_patch(patch)
        ax.add_patch(
            FancyBboxPatch(
                (x_pos + 0.015, 0.49),
                0.05,
                0.035,
                boxstyle="round,pad=0.01,rounding_size=0.02",
                linewidth=0,
                facecolor=accent,
                transform=ax.transAxes,
            )
        )
        ax.text(x_pos + 0.015, 0.45, title, fontsize=11, color="#667382", transform=ax.transAxes)
        ax.text(x_pos + 0.015, 0.25, value, fontsize=20, fontweight="bold", color="#182433", transform=ax.transAxes)
        ax.text(x_pos + 0.015, 0.12, subtitle, fontsize=10, color="#667382", transform=ax.transAxes)

    prev = comparison["vs_previous"]
    avg = comparison["vs_average"]
    summary_lines = [
        f"Vs previous day: active {fmt_delta(prev['active_delta_seconds'])}, deep work {fmt_delta(prev['deep_work_delta_seconds'])}, focus {prev['focus_ratio_delta']:+.1f}pt",
        f"Vs 7-day average: active {fmt_delta(avg['active_delta_seconds'])}, deep work {fmt_delta(avg['deep_work_delta_seconds'])}, focus {avg['focus_ratio_delta']:+.1f}pt",
    ]
    for index, line in enumerate(summary_lines):
        ax.text(0.0, -0.02 - index * 0.08, line, fontsize=10.5, color="#52606d", transform=ax.transAxes)


def render_insights(ax, summary: dict, comparison: dict) -> None:
    ax.set_facecolor("#ffffff")
    ax.axis("off")
    patch = FancyBboxPatch(
        (0.0, 0.0),
        1.0,
        1.0,
        boxstyle="round,pad=0.018,rounding_size=0.03",
        linewidth=1,
        edgecolor="#dce3ee",
        facecolor="#ffffff",
        transform=ax.transAxes,
    )
    ax.add_patch(patch)
    ax.text(0.05, 0.92, "Shareable highlights", fontsize=14, fontweight="bold", color="#182433", transform=ax.transAxes)
    ax.text(
        0.05,
        0.84,
        "Short takeaways for posting to a study or accountability group.",
        fontsize=10,
        color="#667382",
        transform=ax.transAxes,
    )

    top_category = summary["categories"][0]["name"] if summary["categories"] else "No dominant category"
    top_app = summary["top_apps"][0]["name"] if summary["top_apps"] else "No app data"
    top_domain = summary["top_domains"][0]["name"] if summary["top_domains"] else "No browser-domain data yet"
    top_activity = summary["top_activities"][0]["name"] if summary["top_activities"] else "No activity data"
    prev = comparison["vs_previous"]
    lines = [
        f"Primary mode: {top_category}",
        f"Most-used app: {top_app}",
        f"Most-used site: {top_domain}",
        f"Top activity: {top_activity}",
        f"Longest session: {summary['longest_session_label']}",
        f"Change vs previous day: active {fmt_delta(prev['active_delta_seconds'])}, focus {prev['focus_ratio_delta']:+.1f}pt",
    ]
    y_pos = 0.72
    for line in lines:
        wrapped = fill(line, width=38)
        ax.text(0.07, y_pos, f"- {wrapped}", fontsize=11.5, color="#182433", transform=ax.transAxes, va="top")
        y_pos -= 0.12 if "\n" in wrapped else 0.095


def render_report_image(summary: dict, comparison: dict, output_path: Path) -> Path:
    plt.style.use("seaborn-v0_8-whitegrid")
    figure = plt.figure(figsize=(16, 18), facecolor="#f5f7fb", constrained_layout=True)
    axes = figure.subplot_mosaic(
        [
            ["header", "header"],
            ["categories", "hours"],
            ["trend", "trend"],
            ["apps", "domains"],
            ["activities", "insights"],
        ],
        gridspec_kw={"height_ratios": [1.1, 1.05, 1.0, 1.0, 1.0]},
    )

    render_header(axes["header"], summary, comparison)
    render_horizontal_bars(
        axes["categories"],
        "Category breakdown",
        "Time split by category.",
        summary["categories"],
        colors=[item["color"] for item in summary["categories"][:6]],
        fallback="No categorized activity yet.",
    )
    render_hourly_chart(axes["hours"], summary)
    render_trend_chart(axes["trend"], comparison)
    render_horizontal_bars(
        axes["apps"],
        "Top apps",
        "Most time-consuming applications.",
        summary["top_apps"],
        fallback="No app activity recorded.",
    )
    render_horizontal_bars(
        axes["domains"],
        "Top domains",
        "Browser watcher URL/domain usage.",
        summary["top_domains"],
        fallback="No browser-domain data recorded yet.",
    )
    render_horizontal_bars(
        axes["activities"],
        "Top activities",
        "Most time-consuming tabs, windows, or contexts.",
        summary["top_activities"],
        fallback="No activity detail recorded.",
    )
    render_insights(axes["insights"], summary, comparison)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=180, bbox_inches="tight", facecolor=figure.get_facecolor())
    plt.close(figure)
    return output_path


def summarize_day(date_str: Optional[str] = None) -> dict:
    rules = load_rules()
    start_local, end_local = local_day_bounds(date_str)
    start_utc = start_local.astimezone(timezone.utc)
    end_utc = end_local.astimezone(timezone.utc)

    buckets = request_json("/api/0/buckets/")
    bucket_ids = list(buckets.keys())
    window_bucket = choose_bucket(bucket_ids, "aw-watcher-window_")
    afk_bucket = choose_bucket(bucket_ids, "aw-watcher-afk_")
    web_buckets = choose_buckets(bucket_ids, "aw-watcher-web")
    if not window_bucket or not afk_bucket:
        raise RuntimeError("Could not find required ActivityWatch buckets.")

    window_events = fetch_events(window_bucket, start_utc, end_utc)
    afk_events = fetch_events(afk_bucket, start_utc, end_utc)
    web_events: List[dict] = []
    for web_bucket in web_buckets:
        web_events.extend(fetch_events(web_bucket, start_utc, end_utc))
    segments = build_segments_with_web(window_events, web_events, active_intervals(afk_events), rules)
    sessions = merge_sessions(segments)

    total_seconds = sum(item["seconds"] for item in segments)
    productive_seconds = sum(item["seconds"] for item in segments if item["productive"])
    deep_work_seconds = sum(item["seconds"] for item in segments if item.get("deep_work"))

    by_category = defaultdict(float)
    by_subcategory = defaultdict(float)
    by_app = defaultdict(float)
    by_activity = defaultdict(float)
    by_domain = defaultdict(float)
    colors: Dict[str, str] = {}

    for item in segments:
        by_category[item["category"]] += item["seconds"]
        by_subcategory[f'{item["category"]}::{item["subcategory"]}'] += item["seconds"]
        by_app[item["app"]] += item["seconds"]
        by_activity[item["activity"]] += item["seconds"]
        if item.get("domain"):
            by_domain[item["domain"]] += item["seconds"]
        colors[item["category"]] = item["color"]

    category_rows = []
    for category, seconds in sorted(by_category.items(), key=lambda item: item[1], reverse=True):
        sub_rows = []
        for key, sub_seconds in sorted(by_subcategory.items(), key=lambda item: item[1], reverse=True):
            cat_name, sub_name = key.split("::", 1)
            if cat_name != category:
                continue
            sub_rows.append({"name": sub_name, "seconds": sub_seconds, "label": fmt_duration(sub_seconds)})
        category_rows.append(
            {
                "name": category,
                "seconds": seconds,
                "label": fmt_duration(seconds),
                "percent": round((seconds / total_seconds) * 100, 1) if total_seconds else 0.0,
                "color": colors.get(category, "#6b7280"),
                "subcategories": sub_rows,
            }
        )

    focus_blocks = [
        {
            "start": item["start"].astimezone(start_local.tzinfo).strftime("%H:%M"),
            "end": item["end"].astimezone(start_local.tzinfo).strftime("%H:%M"),
            "seconds": item["seconds"],
            "label": fmt_duration(item["seconds"]),
            "category": item["category"],
            "subcategory": item["subcategory"],
            "activity": item["activity"],
            "color": item["color"],
        }
        for item in sorted(
            [session for session in sessions if session.get("deep_work") and session["seconds"] >= 900],
            key=lambda item: item["seconds"],
            reverse=True,
        )[:6]
    ]

    session_rows = [
        {
            "start": item["start"].astimezone(start_local.tzinfo).strftime("%H:%M"),
            "end": item["end"].astimezone(start_local.tzinfo).strftime("%H:%M"),
            "seconds": item["seconds"],
            "label": fmt_duration(item["seconds"]),
            "category": item["category"],
            "subcategory": item["subcategory"],
            "activity": item["activity"],
            "app": item["app"],
            "detail": item.get("url") or item.get("domain") or item["title"],
            "color": item["color"],
        }
        for item in sorted(sessions, key=lambda segment: segment["start"], reverse=True)[:24]
    ]

    context_switches = max(len(sessions) - 1, 0)
    longest_session = max((item["seconds"] for item in sessions), default=0.0)
    focus_ratio = round((productive_seconds / total_seconds) * 100, 1) if total_seconds else 0.0

    return {
        "date": start_local.strftime("%Y-%m-%d"),
        "generated_at": datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z"),
        "total_seconds": total_seconds,
        "total_label": fmt_duration(total_seconds),
        "productive_seconds": productive_seconds,
        "productive_label": fmt_duration(productive_seconds),
        "deep_work_seconds": deep_work_seconds,
        "deep_work_label": fmt_duration(deep_work_seconds),
        "focus_ratio": focus_ratio,
        "longest_session_seconds": longest_session,
        "longest_session_label": fmt_duration(longest_session),
        "context_switches": context_switches,
        "categories": category_rows,
        "top_apps": rank_map(by_app),
        "top_domains": rank_map(by_domain),
        "top_activities": rank_map(by_activity),
        "hours": accumulate_by_hour(segments, start_local),
        "sessions": session_rows,
        "focus_blocks": focus_blocks,
    }


def compare_days(date_str: Optional[str] = None, days: int = 7) -> dict:
    anchor_start, _ = local_day_bounds(date_str)
    daily = []
    for offset in range(days - 1, -1, -1):
        day = (anchor_start - timedelta(days=offset)).strftime("%Y-%m-%d")
        day_summary = summarize_day(day)
        top_category = day_summary["categories"][0]["name"] if day_summary["categories"] else "General"
        daily.append(
            {
                "date": day_summary["date"],
                "total_seconds": day_summary["total_seconds"],
                "total_label": day_summary["total_label"],
                "deep_work_seconds": day_summary["deep_work_seconds"],
                "deep_work_label": day_summary["deep_work_label"],
                "productive_seconds": day_summary["productive_seconds"],
                "productive_label": day_summary["productive_label"],
                "focus_ratio": day_summary["focus_ratio"],
                "context_switches": day_summary["context_switches"],
                "top_category": top_category,
            }
        )

    selected = daily[-1]
    previous = daily[-2] if len(daily) > 1 else None
    baseline = daily[:-1] if len(daily) > 1 else daily
    avg_active = sum(item["total_seconds"] for item in baseline) / max(len(baseline), 1)
    avg_deep = sum(item["deep_work_seconds"] for item in baseline) / max(len(baseline), 1)
    avg_focus = sum(item["focus_ratio"] for item in baseline) / max(len(baseline), 1)

    return {
        "selected_date": selected["date"],
        "daily": daily,
        "vs_previous": {
            "active_delta_seconds": selected["total_seconds"] - (previous["total_seconds"] if previous else 0.0),
            "deep_work_delta_seconds": selected["deep_work_seconds"] - (previous["deep_work_seconds"] if previous else 0.0),
            "focus_ratio_delta": round(selected["focus_ratio"] - (previous["focus_ratio"] if previous else 0.0), 1),
            "context_switch_delta": selected["context_switches"] - (previous["context_switches"] if previous else 0),
            "previous_date": previous["date"] if previous else None,
        },
        "vs_average": {
            "active_delta_seconds": selected["total_seconds"] - avg_active,
            "deep_work_delta_seconds": selected["deep_work_seconds"] - avg_deep,
            "focus_ratio_delta": round(selected["focus_ratio"] - avg_focus, 1),
            "average_active_label": fmt_duration(avg_active),
            "average_deep_work_label": fmt_duration(avg_deep),
            "average_focus_ratio": round(avg_focus, 1),
        },
    }


def build_report_text(summary: dict, comparison: Optional[dict] = None) -> Tuple[str, str]:
    summary_lines = [
        f'Computer usage report {summary["date"]}',
        f'- Total active time: {summary["total_label"]}',
        f'- Deep work: {summary["deep_work_label"]}',
        f'- Focus ratio: {summary["focus_ratio"]}%',
    ]
    if summary["categories"]:
        top_categories = "; ".join(
            f'{item["name"]}: {item["label"]}' for item in summary["categories"][:3]
        )
        summary_lines.append(f"- Top categories: {top_categories}")
    if summary["top_activities"]:
        top_activities = "; ".join(
            f'{item["name"]}: {item["label"]}' for item in summary["top_activities"][:3]
        )
        summary_lines.append(f"- Top activities: {top_activities}")
    if summary["top_domains"]:
        top_domains = "; ".join(
            f'{item["name"]}: {item["label"]}' for item in summary["top_domains"][:3]
        )
        summary_lines.append(f"- Top domains: {top_domains}")
    if comparison:
        prev = comparison["vs_previous"]
        avg = comparison["vs_average"]
        summary_lines.append(
            f'- Vs previous day: active {fmt_delta(prev["active_delta_seconds"])} | deep work {fmt_delta(prev["deep_work_delta_seconds"])} | focus {prev["focus_ratio_delta"]:+.1f}pt'
        )
        summary_lines.append(
            f'- Vs 7-day average: active {fmt_delta(avg["active_delta_seconds"])} | deep work {fmt_delta(avg["deep_work_delta_seconds"])} | focus {avg["focus_ratio_delta"]:+.1f}pt'
        )
    copy_ready = "\n".join(summary_lines)

    body = [
        f'# ActivityWatch Daily Usage Report - {summary["date"]}',
        "",
        f'- Generated at: {summary["generated_at"]}',
        f'- Total active: {summary["total_label"]}',
        f'- Deep work: {summary["deep_work_label"]}',
        f'- Productive time: {summary["productive_label"]}',
        f'- Focus ratio: {summary["focus_ratio"]}%',
        f'- Longest session: {summary["longest_session_label"]}',
        f'- Context switches: {summary["context_switches"]}',
        "",
        "## Copy-ready summary",
        "",
        "```text",
        copy_ready,
        "```",
        "",
        "## Categories",
        "",
    ]
    for item in summary["categories"] or []:
        body.append(f'- {item["name"]}: {item["label"]}')
        for sub in item["subcategories"][:5]:
            body.append(f'  - {sub["name"]}: {sub["label"]}')
    if not summary["categories"]:
        body.append("- No activity recorded yet.")

    body.extend(["", "## Top apps", ""])
    for item in summary["top_apps"] or []:
        body.append(f'- {item["name"]}: {item["label"]}')
    if not summary["top_apps"]:
        body.append("- No activity recorded yet.")

    body.extend(["", "## Top activities", ""])
    for item in summary["top_activities"] or []:
        body.append(f'- {item["name"]}: {item["label"]}')
    if not summary["top_activities"]:
        body.append("- No activity recorded yet.")

    body.extend(["", "## Top domains", ""])
    for item in summary["top_domains"] or []:
        body.append(f'- {item["name"]}: {item["label"]}')
    if not summary["top_domains"]:
        body.append("- No browser-domain data recorded yet.")

    body.extend(["", "## Long focus blocks", ""])
    for item in summary["focus_blocks"] or []:
        body.append(
            f'- {item["start"]}-{item["end"]} | {item["category"]} / {item["subcategory"]} | {item["activity"]} | {item["label"]}'
        )
    if not summary["focus_blocks"]:
        body.append("- No focus block >= 15m yet.")

    if comparison:
        prev = comparison["vs_previous"]
        avg = comparison["vs_average"]
        body.extend(
            [
                "",
                "## Multi-day comparison",
                "",
                f'- Vs previous day ({prev["previous_date"] or "n/a"}): active {fmt_delta(prev["active_delta_seconds"])}, deep work {fmt_delta(prev["deep_work_delta_seconds"])}, focus {prev["focus_ratio_delta"]:+.1f}pt, context switches {prev["context_switch_delta"]:+d}',
                f'- Vs trailing average: active {fmt_delta(avg["active_delta_seconds"])}, deep work {fmt_delta(avg["deep_work_delta_seconds"])}, focus {avg["focus_ratio_delta"]:+.1f}pt',
                "",
                "## Daily trend",
                "",
            ]
        )
        for item in comparison["daily"]:
            body.append(
                f'- {item["date"]}: active {item["total_label"]} | deep work {item["deep_work_label"]} | focus {item["focus_ratio"]}% | top category {item["top_category"]}'
            )

    body.append("")
    return "\n".join(body), copy_ready


def write_image_report(summary: dict, comparison: dict) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    image_path = REPORTS_DIR / f'activitywatch-report-{summary["date"]}.png'
    return render_report_image(summary, comparison, image_path)


def write_report_bundle(date_str: Optional[str] = None) -> dict:
    summary = summarize_day(date_str)
    comparison = compare_days(summary["date"])
    report_text, copy_ready = build_report_text(summary, comparison)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / f'activitywatch-report-{summary["date"]}.md'
    report_path.write_text(report_text, encoding="utf-8")
    image_path = write_image_report(summary, comparison)
    return {
        "summary": summary,
        "comparison": comparison,
        "markdown_path": report_path,
        "image_path": image_path,
        "markdown": report_text,
        "copy_ready": copy_ready,
    }


def write_report(date_str: Optional[str] = None) -> Tuple[Path, dict, str]:
    bundle = write_report_bundle(date_str)
    return bundle["markdown_path"], bundle["summary"], bundle["copy_ready"]


def copy_clipboard(text: str) -> bool:
    return copy_text_to_clipboard(text)
