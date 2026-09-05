import json
import os
import urllib.request
from datetime import date

USERNAME = os.environ.get("GITHUB_USER", "Dhruv-413")
TOKEN = os.environ["GITHUB_TOKEN"]
OUT_PATH = os.environ.get("OUT_PATH", "assets/activity.svg")

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
          }
        }
      }
    }
  }
}
"""

BG = "#282a36"
BORDER = "#44475a"
TEXT = "#f8f8f2"
MUTED = "#6272a4"
LINE = "#ff79c6"
FILL_TOP = "#bd93f9"


def fetch_calendar():
    body = json.dumps({"query": QUERY, "variables": {"login": USERNAME}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={
            "Authorization": f"bearer {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": USERNAME,
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.load(resp)
    return payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def weekly_totals(calendar):
    weeks = []
    for week in calendar["weeks"]:
        days = week["contributionDays"]
        total = sum(d["contributionCount"] for d in days)
        start = days[0]["date"] if days else None
        weeks.append((start, total))
    return weeks


def smoothed_path(points):
    if len(points) < 2:
        return ""
    d = f"M {points[0][0]:.1f} {points[0][1]:.1f} "
    for i in range(len(points) - 1):
        x0, y0 = points[i]
        x1, y1 = points[i + 1]
        mx = (x0 + x1) / 2
        d += f"C {mx:.1f} {y0:.1f}, {mx:.1f} {y1:.1f}, {x1:.1f} {y1:.1f} "
    return d


def render_svg(weeks, total_contributions):
    width, height = 880, 220
    pad_l, pad_r, pad_t, pad_b = 44, 24, 44, 34
    plot_w = width - pad_l - pad_r
    plot_h = height - pad_t - pad_b

    counts = [c for _, c in weeks]
    max_count = max(counts) if counts and max(counts) > 0 else 1
    n = len(weeks)
    step = plot_w / (n - 1) if n > 1 else 0

    points = []
    for i, (_, count) in enumerate(weeks):
        x = pad_l + i * step
        y = pad_t + plot_h - (count / max_count) * plot_h
        points.append((x, y))

    line_path = smoothed_path(points)
    baseline_y = pad_t + plot_h
    area_path = line_path + f"L {points[-1][0]:.1f} {baseline_y:.1f} L {points[0][0]:.1f} {baseline_y:.1f} Z"

    month_labels = []
    seen_months = set()
    for i, (start, _) in enumerate(weeks):
        if not start:
            continue
        month = start[:7]
        if month not in seen_months:
            seen_months.add(month)
            label = date.fromisoformat(start).strftime("%b")
            month_labels.append((points[i][0], label))

    ticks_svg = "".join(
        f'<text x="{x:.1f}" y="{height - 10}" fill="{MUTED}" font-size="11" '
        f'font-family="Segoe UI, Helvetica, Arial, sans-serif" text-anchor="middle">{label}</text>'
        for x, label in month_labels
    )

    grid_svg = "".join(
        f'<line x1="{pad_l}" y1="{pad_t + plot_h * frac:.1f}" x2="{width - pad_r}" '
        f'y2="{pad_t + plot_h * frac:.1f}" stroke="{BORDER}" stroke-width="1" stroke-dasharray="4 4" opacity="0.5" />'
        for frac in (0.25, 0.5, 0.75)
    )

    return f"""<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="areaFill" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="{FILL_TOP}" stop-opacity="0.55" />
      <stop offset="100%" stop-color="{FILL_TOP}" stop-opacity="0" />
    </linearGradient>
  </defs>
  <rect x="1.5" y="1.5" width="{width - 3}" height="{height - 3}" rx="12" fill="{BG}" stroke="{BORDER}" stroke-width="2" />
  <text x="{pad_l}" y="26" fill="{TEXT}" font-size="16" font-weight="600" font-family="Segoe UI, Helvetica, Arial, sans-serif">Activity</text>
  <text x="{width - pad_r}" y="26" fill="{MUTED}" font-size="13" text-anchor="end" font-family="Segoe UI, Helvetica, Arial, sans-serif">{total_contributions:,} contributions this year</text>
  {grid_svg}
  <path d="{area_path}" fill="url(#areaFill)" />
  <path d="{line_path}" fill="none" stroke="{LINE}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" />
  {ticks_svg}
</svg>
"""


def main():
    calendar = fetch_calendar()
    weeks = weekly_totals(calendar)
    svg = render_svg(weeks, calendar["totalContributions"])
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(svg)


if __name__ == "__main__":
    main()
