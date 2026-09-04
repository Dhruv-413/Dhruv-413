#!/usr/bin/env python3
"""Refreshes every generated region of the profile README.

Everything below the banner is built as **markdown**, not as images. That
is a deliberate constraint, and it buys three things an SVG card cannot:

  * It is always theme-correct. A `<picture>` with `prefers-color-scheme`
    follows the reader's operating system rather than their GitHub theme,
    so a reader on a light OS with GitHub set to dark gets a light card on
    a dark page. Markdown cannot get this wrong.
  * The numbers are selectable, searchable, and readable by screen readers.
  * There is no image to break: no proxy cache, no endpoint, no asset.

The only committed images are assets/banner-dark.svg and
assets/banner-light.svg, drawn by scripts/build_banner.py.

Markers written in README.md:
    <!-- snapshot   -->  headline figures
    <!-- grid       -->  contribution year, as a character grid
    <!-- trend      -->  weekly sparkline and monthly totals
    <!-- languages  -->  language split
    <!-- rhythm     -->  commit hour of day, in IST
    <!-- milestones -->  figures worth keeping
    <!-- projects   -->  Selected work: curated copy + live metrics
    <!-- recent     -->  most recently pushed repositories
    <!-- updated    -->  refresh timestamp

Requires only the Python standard library.

Environment:
    GH_PAT / GH_TOKEN / GITHUB_TOKEN   token with read:user (+ repo for
                                       private contribution counts)
    GH_LOGIN                           username, defaults to Dhruv-413
"""

import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from lib.github import IST, WINDOWS, Client, GitHubError  # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
README = os.environ.get("README_PATH", os.path.join(ROOT, "README.md"))
PROJECTS = os.path.join(ROOT, "content", "projects.json")

# Five intensity steps for the contribution grid, chosen so the shape of a
# busy month is legible at a glance in any monospace font.
LEVELS = ("·", "░", "▒", "▓", "█")

# Eight steps for sparklines.
SPARK = "▁▂▃▄▅▆▇█"

# Solid/empty pair for proportion bars.
FULL, EMPTY = "█", "░"
BAR_WIDTH = 22


def bar(fraction, width=BAR_WIDTH):
    filled = int(round(fraction * width))
    return FULL * filled + EMPTY * (width - filled)


def spark(values):
    """Render a sequence as a one-line sparkline."""
    if not values:
        return ""
    peak = max(values)
    if peak <= 0:
        return SPARK[0] * len(values)
    top = len(SPARK) - 1
    return "".join(SPARK[min(int(v / peak * top + 0.5), top)] for v in values)


def _ticks(width, labels):
    """Lay labels at exact character positions under a sparkline.

    Hand-spacing these drifts the moment a sparkline changes length, and
    a misaligned axis is worse than no axis.
    """
    # Grow rather than clip: a label anchored to the final tick needs to
    # overhang, and silently truncating it turns "23" into "2".
    span = max([width] + [start + len(text) for start, text in labels.items()])
    row = [" "] * span
    for start, text in sorted(labels.items()):
        for offset, char in enumerate(text):
            if 0 <= start + offset < span:
                row[start + offset] = char
    return "".join(row).rstrip()


def level(count, busiest):
    """Map one day's count onto the five-step ramp."""
    if count <= 0:
        return 0
    if busiest <= 1:
        return 4
    ratio = count / busiest
    for i, edge in enumerate((0.25, 0.50, 0.75), start=1):
        if ratio <= edge:
            return i
    return 4


def _weeks(days):
    """Group days into calendar weeks, Sunday first, most recent 53."""
    weeks, week = [], []
    for date, count in days:
        if date.weekday() == 6 and week:   # Sunday opens a new column
            weeks.append(week)
            week = []
        week.append((date, count))
    if week:
        weeks.append(week)
    return weeks[-53:]


# --------------------------------------------------------------------------
# Generated blocks
# --------------------------------------------------------------------------


def build_snapshot(d):
    """Headline figures, paired two-up so the block stays compact."""
    busiest_date, busiest_count = d.busiest_day
    current, longest = d.current_streak, d.longest_streak
    left = [
        ("Contributions, last 12 months", f"{d.total_contributions:,}"),
        ("Commits authored", f"{d.commits:,}"),
        ("Pull requests opened", f"{d.pull_requests:,}"),
        ("Code reviews given", f"{d.reviews:,}"),
    ]
    right = [
        ("Public repositories", f"{d.public_repos}"),
        ("Stars earned", f"{d.stars}"),
        ("Current streak", f"{current} day{'s' if current != 1 else ''}"),
        ("Longest streak", f"{longest} days"),
    ]
    out = ["| Activity | | Reach | |", "| :--- | ---: | :--- | ---: |"]
    for (label_a, value_a), (label_b, value_b) in zip(left, right):
        out.append(f"| {label_a} | **{value_a}** | {label_b} | **{value_b}** |")
    if busiest_date:
        out.append(
            f"| Busiest single day | **{busiest_count}** | that day was | "
            f"**{busiest_date:%d %b %Y}** |"
        )
    return "\n".join(out)


def build_grid(d):
    """The contribution year as a character grid.

    Seven weekday rows by fifty-three week columns, the same shape as
    GitHub's own graph, in a fenced block so it lands in a monospace font
    and the columns line up.
    """
    if not d.days:
        return "_No contribution data yet._"

    busiest = max(c for _, c in d.days)
    weeks = _weeks(d.days)

    # Month ruler: each month's abbreviation sits above its first column.
    ruler = [" "] * len(weeks)
    seen = set()
    for col, week in enumerate(weeks):
        first = week[0][0]
        if first.month not in seen and first.day <= 8 and col + 3 <= len(weeks):
            seen.add(first.month)
            for offset, char in enumerate(f"{first:%b}"):
                ruler[col + offset] = char

    rows = {}
    for col, week in enumerate(weeks):
        for date, count in week:
            rows.setdefault((date.weekday() + 1) % 7, {})[col] = count

    labels = ["   ", "Mon", "   ", "Wed", "   ", "Fri", "   "]
    lines = ["    " + "".join(ruler)]
    for row in range(7):
        cells = "".join(
            LEVELS[level(rows.get(row, {}).get(col, 0), busiest)]
            for col in range(len(weeks))
        )
        lines.append(f"{labels[row]} {cells}")

    lines.append("")
    lines.append(
        f"    less {''.join(LEVELS)} more"
        f"         peak {busiest} contributions in a single day"
    )
    return "```text\n" + "\n".join(lines) + "\n```"


def build_trend(d):
    """A weekly sparkline, then the same year broken out by month."""
    weeks = d.weekly_totals
    if not weeks:
        return "_No contribution data yet._"

    monthly = defaultdict(int)
    for date, count in d.days:
        monthly[(date.year, date.month)] += count
    months = sorted(monthly.items())[-12:]
    peak_month = max((total for _, total in months), default=0) or 1

    out = [
        "```text",
        f"    {spark(weeks)}",
        "    " + _ticks(len(weeks), {0: "a year ago", len(weeks) - 9: "this week"}),
        "```",
        "",
        # The sparkline carries the shape; the month-by-month numbers
        # are drill-down, so they go one click away rather than adding
        # twelve rows to the page.
        "<details>",
        "<summary>Month by month</summary>",
        "",
        "| Month | Contributions | |",
        "| :--- | ---: | :--- |",
    ]
    for (year, month), total in months:
        stamp = datetime(year, month, 1)
        out.append(f"| {stamp:%b %Y} | {total} | `{bar(total / peak_month, 18)}` |")
    out += ["", "</details>"]
    return "\n".join(out)


def build_languages(d):
    if not d.languages:
        return "_No language data available._"
    out = ["| Language | Share | |", "| :--- | :--- | ---: |"]
    for name, share in d.languages:
        out.append(f"| **{name}** | `{bar(share)}` | {share * 100:.1f}% |")
    return "\n".join(out)


def build_rhythm(d):
    """Hour of day in IST: a 24-step sparkline, then the four windows."""
    if not d.commit_samples:
        return "_No commit timestamps available._"

    hours = [d.hours.get(h, 0) for h in range(24)]
    out = [
        "```text",
        f"    {spark(hours)}",
        "    " + _ticks(24, {0: "00", 6: "06", 12: "12", 18: "18", 23: "23"})
        + "   IST",
        "```",
        "",
        "| Time of day | Window | Commits | |",
        "| :--- | :--- | ---: | :--- |",
    ]
    for label, window, span in WINDOWS:
        count = sum(d.hours.get(hour, 0) for hour in span)
        share = count / d.commit_samples
        out.append(
            f"| **{label}** | {window} | {count} | "
            f"`{bar(share, 18)}` {share * 100:.0f}% |"
        )

    tail = [f"Peak hour **{d.peak_hour:02d}:00**"]
    if d.busiest_weekday:
        tail.append(f"busiest weekday **{d.busiest_weekday}**")
    out.append("")
    out.append(
        f"{' · '.join(tail)}. Read from {d.commit_samples:,} commit timestamps "
        f"converted to IST (UTC+05:30), rather than assumed from a profile "
        f"setting."
    )
    return "\n".join(out)


def build_milestones(d):
    """What a trophy wall would show, if the trophies were real."""
    busiest_date, busiest_count = d.busiest_day
    distinct = len(
        {
            edge["node"]["name"]
            for repo in d.repos
            for edge in repo["languages"]["edges"]
        }
    )
    rows = [
        (
            "Longest streak",
            f"{d.longest_streak} days",
            "consecutive days with a contribution",
        ),
        (
            "Busiest day",
            f"{busiest_count} contributions",
            f"{busiest_date:%d %B %Y}" if busiest_date else "no data",
        ),
        ("Languages shipped", f"{distinct}", "across public repositories"),
        (
            "On GitHub",
            f"{d.years_on_github:.1f} years",
            f"{d.total_repos} repositories owned, excluding forks",
        ),
    ]
    out = ["| Milestone | Figure | |", "| :--- | ---: | :--- |"]
    out += [
        f"| {label} | **{value}** | <sub>{note}</sub> |" for label, value, note in rows
    ]
    return "\n".join(out)


def _ago(stamp):
    """Human relative time, in whole units, from an ISO timestamp."""
    when = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    delta = datetime.now(timezone.utc) - when
    days = delta.days
    if days <= 0:
        hours = delta.seconds // 3600
        return "just now" if hours < 1 else f"{hours}h ago"
    if days == 1:
        return "yesterday"
    if days < 30:
        return f"{days} days ago"
    months = days // 30
    if months < 12:
        return f"{months} month{'s' if months > 1 else ''} ago"
    years = days // 365
    return f"{years} year{'s' if years > 1 else ''} ago"


def build_projects(d):
    """Curated copy, live metrics.

    Any entry whose repository has been deleted or made private simply
    disappears rather than rendering a dead link.
    """
    try:
        with open(PROJECTS, encoding="utf-8") as handle:
            curated = json.load(handle)["projects"]
    except (OSError, ValueError, KeyError) as exc:
        print(f"warning: cannot read {PROJECTS}: {exc}", file=sys.stderr)
        return "_Project list unavailable._"

    visible = {r["name"]: r for r in d.repos if not r["isPrivate"]}

    rows = []
    for entry in curated:
        repo = visible.get(entry["repo"])
        if not repo:
            continue  # deleted, private, or renamed: drop it silently

        facts = []
        language = (repo.get("primaryLanguage") or {}).get("name")
        if language:
            facts.append(f"<code>{language}</code>")
        if repo["stargazerCount"]:
            star = "star" if repo["stargazerCount"] == 1 else "stars"
            facts.append(f"{repo['stargazerCount']} {star}")
        if repo.get("pushedAt"):
            facts.append(f"updated {_ago(repo['pushedAt'])}")

        rows.append(
            "<tr>\n"
            f'<td width="32%" valign="top"><b><a href="{repo["url"]}">'
            f'{entry["title"]}</a></b><br/><sub>{entry["tagline"]}<br/>'
            f'{"  ·  ".join(facts)}</sub></td>\n'
            f'<td valign="top">{entry["body"]}</td>\n'
            "</tr>"
        )

    if not rows:
        return "_No public projects to show._"
    return "<table>\n" + "\n".join(rows) + "\n</table>"


def build_recent(d):
    """The five most recently pushed public repositories."""
    public = [r for r in d.repos if not r["isPrivate"] and r.get("pushedAt")]
    public.sort(key=lambda r: r["pushedAt"], reverse=True)
    if not public:
        return "_No recent public activity._"

    lines = []
    for repo in public[:5]:
        language = (repo.get("primaryLanguage") or {}).get("name")
        head = f"[**{repo['name']}**]({repo['url']})"
        if repo.get("description"):
            head += f" — {repo['description'].strip().rstrip('.')}"
        tail = [b for b in (language, f"pushed {_ago(repo['pushedAt'])}") if b]
        lines.append(f"- {head}  <sub>{'  ·  '.join(tail)}</sub>")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Assembly
# --------------------------------------------------------------------------

BLOCKS = {
    "snapshot": build_snapshot,
    "grid": build_grid,
    "trend": build_trend,
    "languages": build_languages,
    "rhythm": build_rhythm,
    "milestones": build_milestones,
    "projects": build_projects,
    "recent": build_recent,
}


def replace(content, marker, block):
    pattern = re.compile(
        rf"<!--\s*{marker} starts\s*-->.*?<!--\s*{marker} ends\s*-->",
        re.DOTALL,
    )
    if not pattern.search(content):
        print(f"warning: marker '{marker}' not found, skipping", file=sys.stderr)
        return content
    return pattern.sub(
        f"<!-- {marker} starts -->\n{block}\n<!-- {marker} ends -->", content
    )


def main():
    try:
        data = Client().fetch()
    except GitHubError as exc:
        sys.exit(f"Could not fetch profile data: {exc}")

    with open(README, encoding="utf-8") as handle:
        content = handle.read()

    for marker, builder in BLOCKS.items():
        content = replace(content, marker, builder(data))

    content = replace(
        content,
        "updated",
        f"_Rebuilt from the GitHub GraphQL API on "
        f"{datetime.now(IST):%d %B %Y at %H:%M} IST._",
    )

    with open(README, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(content)

    print(
        f"README rebuilt for {data.login}: {data.total_contributions} "
        f"contributions, longest streak {data.longest_streak}, "
        f"{data.commit_samples} commit timestamps sampled"
    )


if __name__ == "__main__":
    main()
