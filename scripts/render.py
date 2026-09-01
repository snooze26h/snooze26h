#!/usr/bin/env python3
"""Render graphite + vermillion contribution graphics for the profile README.

The palette follows Sitzfleisch: bone ink on a graphite plate, with vermillion
reserved for days that actually ran. Public GitHub stats hosts go down; these
SVGs are generated here and committed, so the profile does not depend on them.
"""

from __future__ import annotations

import json
import os
import subprocess
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

USER = "snooze26h"
ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"

BED = "#0E0E10"
PLATE = "#1B1B1E"
INK_HIGH = "#EDEAE3"
INK_BODY = "#CBC7BE"
INK_MUTED = "#A5A098"
INK_FAINT = "#89847B"
SIGNAL = "#C7452F"
HAIR = "rgba(255,255,255,0.085)"

# 0 contributions, then four rising bins. Empty cells stay plate-colored so
# the year reads as an etched panel, not a candy heatmap.
LEVELS = (PLATE, "#3D221E", "#6E332B", "#A03E30", SIGNAL)

FONT = "ui-sans-serif, system-ui, -apple-system, Segoe UI, Helvetica, Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      totalCommitContributions
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            contributionCount
            date
            weekday
          }
        }
      }
    }
    repositories(ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC) {
      totalCount
    }
  }
}
"""


def github_token() -> str:
    for key in ("GITHUB_TOKEN", "GH_TOKEN"):
        value = os.environ.get(key)
        if value:
            return value
    return subprocess.check_output(["gh", "auth", "token"], text=True).strip()


def graphql(query: str, variables: dict) -> dict:
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={
            "Authorization": f"Bearer {github_token()}",
            "Content-Type": "application/json",
            "User-Agent": "snooze26h-profile",
        },
        method="POST",
    )
    with urllib.request.urlopen(request) as response:
        payload = json.load(response)
    if payload.get("errors"):
        raise SystemExit(json.dumps(payload["errors"], indent=2))
    return payload["data"]


def level_for(count: int, max_count: int) -> int:
    if count <= 0:
        return 0
    if max_count <= 1:
        return 4
    ratio = count / max_count
    if ratio > 0.75:
        return 4
    if ratio > 0.5:
        return 3
    if ratio > 0.25:
        return 2
    return 1


def esc(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def render_heatmap(weeks: list[dict], total: int) -> str:
    cell = 12
    gap = 3
    step = cell + gap
    pad_left = 36
    pad_top = 38
    pad_right = 18
    pad_bottom = 28
    width = 888
    height = pad_top + 7 * step + pad_bottom
    counts = [
        day["contributionCount"]
        for week in weeks
        for day in week["contributionDays"]
    ]
    max_count = max(counts, default=0)

    month_marks: list[tuple[int, str]] = []
    last_month = None
    for index, week in enumerate(weeks):
        for day in week["contributionDays"]:
            current = date.fromisoformat(day["date"])
            if current.day == 1 and current.strftime("%b") != last_month:
                month_marks.append((index, current.strftime("%b")))
                last_month = current.strftime("%b")
                break
    filtered = []
    last_index = -99
    for index, label in month_marks:
        if index - last_index >= 2:
            filtered.append((index, label))
            last_index = index

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img">',
        f"<title>{total} contributions this year</title>",
        f'<rect width="{width}" height="{height}" rx="6" fill="{BED}"/>',
        f'<text x="16" y="22" fill="{INK_HIGH}" font-family="{FONT}" font-size="13" font-weight="600">this year</text>',
        f'<text x="{width - 16}" y="22" fill="{INK_MUTED}" font-family="{MONO}" font-size="12" text-anchor="end">{total}</text>',
    ]
    for index, label in filtered:
        x = pad_left + index * step
        parts.append(
            f'<text x="{x}" y="34" fill="{INK_FAINT}" font-family="{FONT}" font-size="10">{esc(label)}</text>'
        )
    for weekday, label in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        y = pad_top + weekday * step + cell - 1
        parts.append(
            f'<text x="8" y="{y}" fill="{INK_FAINT}" font-family="{FONT}" font-size="9">{label}</text>'
        )
    for week_index, week in enumerate(weeks):
        for day in week["contributionDays"]:
            x = pad_left + week_index * step
            y = pad_top + day["weekday"] * step
            fill = LEVELS[level_for(day["contributionCount"], max_count)]
            parts.append(
                f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2" fill="{fill}">'
                f'<title>{day["date"]} · {day["contributionCount"]}</title></rect>'
            )
    legend_x = width - 16 - 5 * step
    legend_y = height - 18
    parts.append(
        f'<text x="{legend_x - 6}" y="{legend_y + 9}" fill="{INK_FAINT}" font-family="{FONT}" font-size="9" text-anchor="end">less</text>'
    )
    for index, fill in enumerate(LEVELS):
        parts.append(
            f'<rect x="{legend_x + index * step}" y="{legend_y}" width="{cell}" height="{cell}" rx="2" fill="{fill}"/>'
        )
    parts.append(
        f'<text x="{legend_x + 5 * step + 4}" y="{legend_y + 9}" fill="{INK_FAINT}" font-family="{FONT}" font-size="9">more</text>'
    )
    parts.append("</svg>")
    return "\n".join(parts)


def render_activity(weeks: list[dict]) -> str:
    days = [day for week in weeks for day in week["contributionDays"]]
    days.sort(key=lambda item: item["date"])
    window = days[-31:]
    if not window:
        window = [{"date": date.today().isoformat(), "contributionCount": 0}]
    width, height = 888, 168
    pad_left, pad_right, pad_top, pad_bottom = 16, 16, 40, 28
    plot_w = width - pad_left - pad_right
    plot_h = height - pad_top - pad_bottom
    values = [item["contributionCount"] for item in window]
    peak = max(values + [1])
    n = len(window)
    xs = [
        pad_left + (plot_w * i / max(n - 1, 1)) for i in range(n)
    ]
    ys = [
        pad_top + plot_h - (plot_h * value / peak) for value in values
    ]
    points = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys))
    area = (
        f"{pad_left:.1f},{pad_top + plot_h:.1f} "
        + points
        + f" {xs[-1]:.1f},{pad_top + plot_h:.1f}"
    )
    start = datetime.fromisoformat(window[0]["date"]).strftime("%b %d")
    end = datetime.fromisoformat(window[-1]["date"]).strftime("%b %d")
    total = sum(values)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img">',
        "<title>contributions over the last 31 days</title>",
        f'<rect width="{width}" height="{height}" rx="6" fill="{BED}"/>',
        f'<text x="16" y="22" fill="{INK_HIGH}" font-family="{FONT}" font-size="13" font-weight="600">last 31 days</text>',
        f'<text x="{width - 16}" y="22" fill="{INK_MUTED}" font-family="{MONO}" font-size="12" text-anchor="end">{total} · {start}–{end}</text>',
        f'<line x1="{pad_left}" y1="{pad_top + plot_h}" x2="{width - pad_right}" y2="{pad_top + plot_h}" stroke="{HAIR}" stroke-width="1"/>',
        f'<polygon points="{area}" fill="{SIGNAL}" fill-opacity="0.18"/>',
        f'<polyline points="{points}" fill="none" stroke="{SIGNAL}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>',
    ]
    last_nonzero = max((i for i, value in enumerate(values) if value), default=None)
    if last_nonzero is not None:
        parts.append(
            f'<circle cx="{xs[last_nonzero]:.1f}" cy="{ys[last_nonzero]:.1f}" r="3.5" fill="{SIGNAL}"/>'
        )
    parts.append("</svg>")
    return "\n".join(parts)


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    data = graphql(QUERY, {"login": USER})
    calendar = data["user"]["contributionsCollection"]["contributionCalendar"]
    weeks = calendar["weeks"]
    total = calendar["totalContributions"]
    (ASSETS / "contributions.svg").write_text(render_heatmap(weeks, total) + "\n", encoding="utf-8")
    (ASSETS / "activity.svg").write_text(render_activity(weeks) + "\n", encoding="utf-8")
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    print(f"rendered {total} contributions · {generated}")


if __name__ == "__main__":
    main()
