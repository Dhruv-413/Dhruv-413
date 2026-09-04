#!/usr/bin/env python3
"""Refreshes every generated region of the profile README.

One GraphQL pass produces three things:

  1. Markdown between HTML comment markers in README.md:
         <!-- snapshot  -->  headline figures as a table
         <!-- languages -->  language split as a table
         <!-- rhythm    -->  commit windows as a table
         <!-- projects  -->  Selected work: curated copy + live metrics
         <!-- recent    -->  most recently pushed repositories
         <!-- graphs    -->  the <picture> blocks for the six cards
         <!-- snake     -->  the contribution snake, once it exists
         <!-- updated   -->  the refresh timestamp

  2. Fallback SVG cards in assets/, one file per theme. These keep being
     generated even while the live endpoint is healthy, because they are
     what the README falls back to when the endpoint is not.

  3. Nothing else. Prose stays hand-written.

Requires only the Python standard library.

Environment:
    GH_PAT / GH_TOKEN / GITHUB_TOKEN   token with read:user (+ repo for
                                       private contribution counts)
    GH_LOGIN                           username, defaults to Dhruv-413
    LIVE_BASE                          endpoint for live cards; empty
                                       string pins the README to the
                                       committed assets instead
"""

import json
import os
import re
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from lib import cards  # noqa: E402
from lib.github import IST, Client, GitHubError  # noqa: E402
from lib.theme import THEMES  # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
README = os.environ.get("README_PATH", os.path.join(ROOT, "README.md"))
ASSETS = os.environ.get("ASSETS_DIR", os.path.join(ROOT, "assets"))
PROJECTS = os.path.join(ROOT, "content", "projects.json")

# The live endpoint, e.g. "https://<app>.vercel.app/api/card".
#
# Empty means serve the committed assets, and empty is the correct default:
# a repository that points at a deployment which does not exist yet renders
# six broken images on the profile page. Fill this in only once the
# deployment answers, and it doubles as the kill switch if it ever stops.
LIVE_BASE = os.environ.get("LIVE_BASE", "")

FULL = "█"
EMPTY = "░"
BAR_WIDTH = 22

# Order matters: this is the reading order of the "By the numbers" section.
GRAPH_ORDER = [
    ("snapshot", "Headline figures for the last twelve months"),
    ("contributions", "Contribution graph for the last year"),
    ("activity", "Contributions per week over the last year"),
    ("languages", "Language footprint across my repositories"),
    ("rhythm", "Commit rhythm by hour of day, in IST"),
    ("milestones", "Milestones computed from my own history"),
]


def bar(fraction, width=BAR_WIDTH):
    filled = int(round(fraction * width))
    return FULL * filled + EMPTY * (width - filled)


# --------------------------------------------------------------------------
# Markdown blocks
# --------------------------------------------------------------------------


def build_snapshot(d):
    busiest_date, busiest_count = d.busiest_day
    current, longest = d.current_streak, d.longest_streak
    rows = [
        ("Contributions, last 12 months", f"{d.total_contributions:,}"),
        ("Commits", f"{d.commits:,}"),
        ("Pull requests opened", f"{d.pull_requests:,}"),
        ("Issues opened", f"{d.issues:,}"),
        ("Reviews given", f"{d.reviews:,}"),
        ("Public repositories", f"{d.public_repos}"),
        ("Stars earned", f"{d.stars}"),
        ("Current streak", f"{current} day{'s' if current != 1 else ''}"),
        ("Longest streak", f"{longest} days"),
        (
            "Busiest single day",
            f"{busiest_count} contributions on {busiest_date:%d %b %Y}"
            if busiest_date
            else "no data",
        ),
        ("On GitHub for", f"{d.years_on_github:.1f} years"),
    ]
    out = ["| | |", "| :--- | ---: |"]
    out += [f"| {label} | **{value}** |" for label, value in rows]
    return "\n".join(out)


def build_languages(d):
    if not d.languages:
        return "_No language data available._"
    out = ["| Language | Share | |", "| :--- | :--- | ---: |"]
    for name, share in d.languages:
        out.append(f"| **{name}** | `{bar(share)}` | {share * 100:.1f}% |")
    return "\n".join(out)


def build_rhythm(d):
    out = [
        "| Time of day (IST) | Window | Commits | |",
        "| :--- | :--- | ---: | :--- |",
    ]
    if not d.commit_samples:
        out.append("| _No commit timestamps available_ | | | |")
    else:
        for label, window, span in cards.WINDOWS:
            count = sum(d.hours.get(h, 0) for h in span)
            share = count / d.commit_samples
            out.append(
                f"| **{label}** | {window} | {count} | "
                f"`{bar(share, 18)}` {share * 100:.0f}% |"
            )
    if d.busiest_weekday:
        out.append("")
        out.append(
            f"Most active day of the week: **{d.busiest_weekday}**. All times "
            f"are IST (UTC+5:30), computed from commit timestamps rather than "
            f"assumed."
        )
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
            f'<td width="30%" valign="top"><b><a href="{repo["url"]}">'
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
        bits = [f"[**{repo['name']}**]({repo['url']})"]
        if repo.get("description"):
            bits.append(repo["description"].strip().rstrip("."))
        tail = [b for b in (language, f"pushed {_ago(repo['pushedAt'])}") if b]
        lines.append(f"- {' — '.join(bits)}  <sub>{'  ·  '.join(tail)}</sub>")
    return "\n".join(lines)


def build_snake(stamp):
    """Reference the snake only once the Action has actually produced it.

    Without this check a fresh clone advertises two files that do not
    exist yet, which is two broken images on the profile until the first
    scheduled run completes.
    """
    if not os.path.exists(os.path.join(ASSETS, "snake-light.svg")):
        return "_The snake is generated by the scheduled build._"
    return (
        "<picture>\n"
        '  <source media="(prefers-color-scheme: dark)" '
        f'srcset="./assets/snake-dark.svg?v={stamp}">\n'
        '  <source media="(prefers-color-scheme: light)" '
        f'srcset="./assets/snake-light.svg?v={stamp}">\n'
        '  <img alt="A snake consuming my contribution graph" '
        f'src="./assets/snake-light.svg?v={stamp}" width="100%">\n'
        "</picture>"
    )


def build_graphs(stamp):
    """The <picture> blocks.

    Live endpoint when LIVE_BASE is set, committed assets otherwise. The
    cache-busting stamp only matters in the committed case: Camo caches
    aggressively, so without a changing URL a refreshed SVG can keep
    serving yesterday's numbers.
    """
    blocks = []
    for name, alt in GRAPH_ORDER:
        if LIVE_BASE:
            dark = f"{LIVE_BASE}?card={name}&amp;theme=dark"
            light = f"{LIVE_BASE}?card={name}&amp;theme=light"
        else:
            dark = f"./assets/{name}-dark.svg?v={stamp}"
            light = f"./assets/{name}-light.svg?v={stamp}"
        blocks.append(
            "<picture>\n"
            f'  <source media="(prefers-color-scheme: dark)" srcset="{dark}">\n'
            f'  <source media="(prefers-color-scheme: light)" srcset="{light}">\n'
            f'  <img alt="{alt}" src="{light}" width="100%">\n'
            "</picture>"
        )
    return "\n\n".join(blocks)


# --------------------------------------------------------------------------
# Assembly
# --------------------------------------------------------------------------


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

    os.makedirs(ASSETS, exist_ok=True)
    for theme_name, theme in THEMES.items():
        for card_name, render in cards.CARDS.items():
            path = os.path.join(ASSETS, f"{card_name}-{theme_name}.svg")
            with open(path, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(render(theme, data) + "\n")
    print(f"wrote {len(cards.CARDS) * len(THEMES)} fallback cards to assets/")

    with open(README, encoding="utf-8") as handle:
        content = handle.read()

    stamp = f"{datetime.now(IST):%Y%m%d%H}"
    content = replace(content, "snapshot", build_snapshot(data))
    content = replace(content, "languages", build_languages(data))
    content = replace(content, "rhythm", build_rhythm(data))
    content = replace(content, "projects", build_projects(data))
    content = replace(content, "recent", build_recent(data))
    content = replace(content, "graphs", build_graphs(stamp))
    content = replace(content, "snake", build_snake(stamp))
    content = replace(
        content,
        "updated",
        f"_Last refreshed {datetime.now(IST):%d %B %Y, %H:%M} IST "
        f"· {'live cards served from the endpoint' if LIVE_BASE else 'serving committed cards'}._",
    )

    with open(README, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(content)

    print(
        f"README updated for {data.login}: {data.total_contributions} "
        f"contributions, longest streak {data.longest_streak}, "
        f"{data.commit_samples} commit timestamps sampled"
    )


if __name__ == "__main__":
    main()
