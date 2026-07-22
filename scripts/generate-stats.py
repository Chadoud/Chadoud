#!/usr/bin/env python3
"""Generate equal-width github-stats.svg and top-langs.svg for 50/50 README layout."""

from __future__ import annotations

import json
import os
import subprocess
import urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
USERNAME = os.environ.get("GH_USERNAME", "Chadoud")
INDIGO = "#6366F1"
BG = "#0d1117"
TEXT = "#c9d1d9"
MUTED = "#8b949e"

# Same canvas for both cards so width="49%" scales evenly
CARD_W = 560
CARD_H = 180


def gh_api(path: str):
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        req = urllib.request.Request(
            f"https://api.github.com{path}",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "User-Agent": "Chadoud-profile-stats",
            },
        )
        with urllib.request.urlopen(req) as resp:
            return json.load(resp)
    return json.loads(
        subprocess.check_output(["gh", "api", path.lstrip("/")], text=True)
    )


def gh_graphql(query: str) -> dict:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        body = json.dumps({"query": query}).encode()
        req = urllib.request.Request(
            "https://api.github.com/graphql",
            data=body,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "User-Agent": "Chadoud-profile-stats",
            },
            method="POST",
        )
        with urllib.request.urlopen(req) as resp:
            return json.load(resp)
    return json.loads(
        subprocess.check_output(["gh", "api", "graphql", "-f", f"query={query}"], text=True)
    )


def main() -> None:
    gql = gh_graphql(
        f'''query {{
          user(login: "{USERNAME}") {{
            contributionsCollection {{
              contributionCalendar {{ totalContributions }}
            }}
          }}
        }}'''
    )
    total_contrib = gql["data"]["user"]["contributionsCollection"]["contributionCalendar"][
        "totalContributions"
    ]

    repos = gh_api("/user/repos?per_page=100&affiliation=owner&sort=updated")
    owned = [r for r in repos if not r.get("fork")]
    langs = Counter(r["language"] for r in owned if r.get("language"))
    public_count = sum(1 for r in owned if not r.get("private"))

    w, h = CARD_W, CARD_H
    rows = [
        ("Contributions (year)", f"{total_contrib:,}", INDIGO),
        ("Repositories", str(len(owned)), TEXT),
        ("Public repositories", str(public_count), TEXT),
    ]
    lines = []
    for i, (label, val, color) in enumerate(rows):
        y = 72 + i * 32
        lines.append(
            f'<text x="32" y="{y}" fill="{MUTED}" font-size="14" '
            f'font-family="Segoe UI, Ubuntu, Sans-Serif">{label}</text>'
            f'<text x="{w - 32}" y="{y}" text-anchor="end" fill="{color}" font-size="16" '
            f'font-weight="600" font-family="Segoe UI, Ubuntu, Sans-Serif">{val}</text>'
        )
    stats = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="GitHub stats">
  <rect width="100%" height="100%" rx="8" fill="{BG}" stroke="#30363d"/>
  <text x="32" y="36" fill="{INDIGO}" font-size="18" font-weight="600" font-family="Segoe UI, Ubuntu, Sans-Serif">GitHub Stats</text>
  <line x1="32" y1="50" x2="{w - 32}" y2="50" stroke="#21262d"/>
  {"".join(lines)}
</svg>
'''
    (ROOT / "assets" / "github-stats.svg").write_text(stats, encoding="utf-8")

    items = langs.most_common(5)
    total = sum(c for _, c in items) or 1
    colors = [INDIGO, "#818CF8", "#A5B4FC", "#4F46E5", "#4338CA"]
    bar_x = 140
    bar_max = w - bar_x - 56
    bars = []
    for i, (lang, n) in enumerate(items):
        y = 72 + i * 20
        bw = max(4, int(bar_max * (n / total)))
        bars.append(
            f'<text x="32" y="{y}" fill="{TEXT}" font-size="13" '
            f'font-family="Segoe UI, Ubuntu, Sans-Serif">{lang}</text>'
            f'<rect x="{bar_x}" y="{y - 10}" width="{bar_max}" height="10" rx="3" fill="#21262d"/>'
            f'<rect x="{bar_x}" y="{y - 10}" width="{bw}" height="10" rx="3" fill="{colors[i % len(colors)]}"/>'
            f'<text x="{w - 32}" y="{y}" text-anchor="end" fill="{MUTED}" font-size="12" '
            f'font-family="Segoe UI, Ubuntu, Sans-Serif">{n}</text>'
        )
    langs_svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="Top languages">
  <rect width="100%" height="100%" rx="8" fill="{BG}" stroke="#30363d"/>
  <text x="32" y="36" fill="{INDIGO}" font-size="18" font-weight="600" font-family="Segoe UI, Ubuntu, Sans-Serif">Top Languages</text>
  <line x1="32" y1="50" x2="{w - 32}" y2="50" stroke="#21262d"/>
  {"".join(bars)}
</svg>
'''
    (ROOT / "assets" / "top-langs.svg").write_text(langs_svg, encoding="utf-8")
    print(f"Wrote equal {w}x{h} cards ({total_contrib} contrib, {len(owned)} repos)")


if __name__ == "__main__":
    main()
