#!/usr/bin/env python3
"""Generate assets/activity-graph.svg from real GitHub contribution data."""

from __future__ import annotations

import json
import math
import os
import subprocess
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "activity-graph.svg"
USERNAME = os.environ.get("GH_USERNAME", "Chadoud")
DAYS = 30
INDIGO = "#6366F1"
BG = "#0d1117"
TEXT = "#c9d1d9"
GRID = "#21262d"


def fetch_days() -> list[dict]:
    query = """
    query($login: String!) {
      user(login: $login) {
        contributionsCollection {
          contributionCalendar {
            weeks { contributionDays { date contributionCount } }
          }
        }
      }
    }
    """
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        body = json.dumps({"query": query, "variables": {"login": USERNAME}}).encode()
        req = urllib.request.Request(
            "https://api.github.com/graphql",
            data=body,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "User-Agent": "Chadoud-activity-graph",
            },
            method="POST",
        )
        with urllib.request.urlopen(req) as resp:
            payload = json.load(resp)
    else:
        raw = subprocess.check_output(
            [
                "gh",
                "api",
                "graphql",
                "-f",
                f"query={query}",
                "-F",
                f"login={USERNAME}",
            ],
            text=True,
        )
        payload = json.loads(raw)

    weeks = payload["data"]["user"]["contributionsCollection"]["contributionCalendar"][
        "weeks"
    ]
    days: list[dict] = []
    for week in weeks:
        days.extend(week["contributionDays"])
    return days[-DAYS:]


def nice_max(n: int) -> int:
    if n <= 5:
        return 5
    if n <= 10:
        return 10
    if n <= 20:
        return 20
    return int(math.ceil(n / 5) * 5)


def build_svg(days: list[dict]) -> str:
    counts = [d["contributionCount"] for d in days]
    dates = [d["date"] for d in days]
    total = sum(counts)
    ymax = nice_max(max(counts) if counts else 1)

    w, h = 1200, 380
    pad_l, pad_r, pad_t, pad_b = 56, 40, 64, 52
    plot_w = w - pad_l - pad_r
    plot_h = h - pad_t - pad_b

    def x_at(i: int) -> float:
        if len(counts) <= 1:
            return pad_l + plot_w / 2
        return pad_l + i * plot_w / (len(counts) - 1)

    def y_at(c: int) -> float:
        return pad_t + plot_h * (1 - c / ymax)

    pts = [(x_at(i), y_at(c)) for i, c in enumerate(counts)]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    area = (
        f"M {pts[0][0]:.1f},{pad_t + plot_h:.1f} "
        + " ".join(f"L {x:.1f},{y:.1f}" for x, y in pts)
        + f" L {pts[-1][0]:.1f},{pad_t + plot_h:.1f} Z"
    )

    label_idx = sorted(set([0, len(days) - 1] + list(range(0, len(days), 5))))

    def fmt_date(s: str) -> str:
        return datetime.strptime(s, "%Y-%m-%d").strftime("%b %d")

    step = max(1, ymax // 4)
    yticks = list(range(0, ymax + 1, step))

    circles = "\n".join(
        f'  <circle cx="{x:.1f}" cy="{y:.1f}" r="4.5" fill="{INDIGO}" stroke="{BG}" stroke-width="2"/>'
        for x, y in pts
    )
    xlabels = "\n".join(
        f'  <text x="{x_at(i):.1f}" y="{h - 18}" text-anchor="middle" fill="{TEXT}" '
        f'font-size="12" font-family="Segoe UI, Ubuntu, Sans-Serif">{fmt_date(dates[i])}</text>'
        for i in label_idx
    )
    grids = "\n".join(
        f'  <line x1="{pad_l}" y1="{y_at(v):.1f}" x2="{w - pad_r}" y2="{y_at(v):.1f}" '
        f'stroke="{GRID}" stroke-width="1"/>'
        for v in yticks
    )
    ylabels = "\n".join(
        f'  <text x="{pad_l - 12}" y="{y_at(v) + 4:.1f}" text-anchor="end" fill="{TEXT}" '
        f'font-size="12" font-family="Segoe UI, Ubuntu, Sans-Serif">{v}</text>'
        for v in yticks
    )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" fill="none" role="img" aria-label="GitHub activity — last {DAYS} days">
  <rect width="100%" height="100%" rx="8" fill="{BG}"/>
  <text x="{w / 2}" y="36" text-anchor="middle" fill="{INDIGO}" font-size="20" font-weight="600" font-family="Segoe UI, Ubuntu, Sans-Serif">GitHub Activity (last {DAYS} days)</text>
  <text x="{w - pad_r}" y="36" text-anchor="end" fill="{TEXT}" font-size="12" font-family="Segoe UI, Ubuntu, Sans-Serif">{total} contributions</text>
{grids}
  <path d="{area}" fill="{INDIGO}" fill-opacity="0.18"/>
  <polyline fill="none" stroke="{INDIGO}" stroke-width="3" stroke-linejoin="round" stroke-linecap="round" points="{line}"/>
{circles}
{ylabels}
{xlabels}
  <text x="{pad_l}" y="{h - 6}" fill="#8b949e" font-size="11" font-family="Segoe UI, Ubuntu, Sans-Serif">Source: GitHub contribution calendar</text>
</svg>
'''


def main() -> None:
    days = fetch_days()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(build_svg(days), encoding="utf-8")
    print(f"Wrote {OUT} ({sum(d['contributionCount'] for d in days)} contributions / {DAYS}d)")


if __name__ == "__main__":
    main()
