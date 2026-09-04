#!/usr/bin/env python3
"""
Builds the dynamic sections of the profile README from the GitHub GraphQL API.

Writes between HTML comment markers in README.md:
    <!-- snapshot starts --> ... <!-- snapshot ends -->
    <!-- languages starts --> ... <!-- languages ends -->
    <!-- rhythm starts -->   ... <!-- rhythm ends -->
    <!-- updated starts -->  ... <!-- updated ends -->

Requires only the Python standard library.
Environment:
    GH_TOKEN  personal access token with read:user (and repo, if you want
              private contributions counted)
    GH_LOGIN  GitHub username (defaults to Dhruv-413)
"""

import json
import os
import re
import sys
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

API = "https://api.github.com/graphql"
TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
LOGIN = os.environ.get("GH_LOGIN", "Dhruv-413")
IST = ZoneInfo("Asia/Kolkata")
README = os.environ.get("README_PATH", "README.md")

FULL = "\u2588"  # full block
EMPTY = "\u2591"  # light shade
BAR_WIDTH = 22


def gql(query, variables):
    """POST a GraphQL query and return the data payload."""
    body = json.dumps({"query": query, "variables": variables}).encode()
    req = urllib.request.Request(
        API,
        data=body,
        headers={
            "Authorization": f"bearer {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": f"{LOGIN}-profile-readme",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            payload = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        sys.exit(f"GraphQL HTTP {exc.code}: {exc.read().decode()[:400]}")
    if "errors" in payload:
        sys.exit(f"GraphQL errors: {json.dumps(payload['errors'])[:600]}")
    return payload["data"]


PROFILE_QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    id
    createdAt
    followers { totalCount }
    contributionsCollection(from: $from, to: $to) {
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
      totalPullRequestReviewContributions
      restrictedContributionsCount
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount weekday } }
      }
    }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false,
                 orderBy: {field: PUSHED_AT, direction: DESC}) {
      totalCount
      nodes {
        name
        stargazerCount
        isPrivate
        languages(first: 12, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name } }
        }
      }
    }
  }
}
"""

HISTORY_QUERY = """
query($login: String!, $name: String!, $uid: ID!, $since: GitTimestamp!) {
  repository(owner: $login, name: $name) {
    defaultBranchRef {
      target {
        ... on Commit {
          history(first: 100, author: {id: $uid}, since: $since) {
            nodes { committedDate }
          }
        }
      }
    }
  }
}
"""


def bar(fraction, width=BAR_WIDTH):
    filled = int(round(fraction * width))
    return FULL * filled + EMPTY * (width - filled)


def compute_streaks(days):
    """days: list of (date, count) sorted ascending. Returns (current, longest)."""
    longest = run = 0
    for _, count in days:
        run = run + 1 if count > 0 else 0
        longest = max(longest, run)

    current = 0
    today = datetime.now(IST).date()
    for date, count in reversed(days):
        if date > today:
            continue
        if count > 0:
            current += 1
        elif date == today:
            continue  # today may simply not have happened yet
        else:
            break
    return current, longest


def build_snapshot(user, days, current, longest):
    cc = user["contributionsCollection"]
    repos = user["repositories"]
    stars = sum(r["stargazerCount"] for r in repos["nodes"])
    public_repos = sum(1 for r in repos["nodes"] if not r["isPrivate"])
    joined = datetime.fromisoformat(user["createdAt"].replace("Z", "+00:00"))
    years = (datetime.now(timezone.utc) - joined).days / 365.25
    busiest = max(days, key=lambda d: d[1])

    rows = [
        (
            "Contributions, last 12 months",
            f"{cc['contributionCalendar']['totalContributions']:,}",
        ),
        ("Commits", f"{cc['totalCommitContributions']:,}"),
        ("Pull requests opened", f"{cc['totalPullRequestContributions']:,}"),
        ("Issues opened", f"{cc['totalIssueContributions']:,}"),
        ("Reviews given", f"{cc['totalPullRequestReviewContributions']:,}"),
        ("Public repositories", f"{public_repos}"),
        ("Stars earned", f"{stars}"),
        ("Current streak", f"{current} day{'s' if current != 1 else ''}"),
        ("Longest streak", f"{longest} days"),
        ("Busiest single day", f"{busiest[1]} contributions on {busiest[0]:%d %b %Y}"),
        ("On GitHub for", f"{years:.1f} years"),
    ]
    out = ["| | |", "| :--- | ---: |"]
    out += [f"| {label} | **{value}** |" for label, value in rows]
    return "\n".join(out)


def build_languages(user):
    totals = defaultdict(int)
    for repo in user["repositories"]["nodes"]:
        for edge in repo["languages"]["edges"]:
            totals[edge["node"]["name"]] += edge["size"]
    if not totals:
        return "_No language data available._"

    grand = sum(totals.values())
    ranked = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)[:6]

    out = ["| Language | Share | |", "| :--- | :--- | ---: |"]
    for name, size in ranked:
        share = size / grand
        out.append(f"| **{name}** | `{bar(share)}` | {share * 100:.1f}% |")
    return "\n".join(out)


def build_rhythm(user, days):
    """Commit hour histogram, computed in IST rather than UTC."""
    uid = user["id"]
    since = (datetime.now(timezone.utc) - timedelta(days=365)).isoformat()
    hours = defaultdict(int)
    total = 0

    for repo in user["repositories"]["nodes"][:30]:
        data = gql(
            HISTORY_QUERY,
            {
                "login": LOGIN,
                "name": repo["name"],
                "uid": uid,
                "since": since,
            },
        )
        ref = (data.get("repository") or {}).get("defaultBranchRef")
        if not ref or not ref.get("target"):
            continue
        for node in ref["target"].get("history", {}).get("nodes", []):
            stamp = datetime.fromisoformat(node["committedDate"].replace("Z", "+00:00"))
            hours[stamp.astimezone(IST).hour] += 1
            total += 1

    blocks = [
        ("Early morning", "05:00 - 09:00", range(5, 9)),
        ("Daytime", "09:00 - 17:00", range(9, 17)),
        ("Evening", "17:00 - 22:00", range(17, 22)),
        ("Late night", "22:00 - 05:00", list(range(22, 24)) + list(range(0, 5))),
    ]

    out = [
        "| Time of day (IST) | Window | Commits | |",
        "| :--- | :--- | ---: | :--- |",
    ]

    if total == 0:
        out.append("| _No commit timestamps available_ | | | |")
    else:
        for label, window, span in blocks:
            count = sum(hours[h] for h in span)
            share = count / total
            out.append(
                f"| **{label}** | {window} | {count} | `{bar(share, 18)}` {share * 100:.0f}% |"
            )

    weekday_names = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]
    weekday = defaultdict(int)
    for date, count in days:
        weekday[date.weekday()] += count
    if weekday:
        best = max(weekday.items(), key=lambda kv: kv[1])
        out.append("")
        out.append(
            f"Most active day of the week: **{weekday_names[best[0]]}**. "
            f"All times above are IST (UTC+5:30), computed from commit "
            f"timestamps rather than assumed."
        )
    return "\n".join(out)


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
    if not TOKEN:
        sys.exit("Set GH_TOKEN (or GITHUB_TOKEN) before running.")

    now = datetime.now(timezone.utc)
    data = gql(
        PROFILE_QUERY,
        {
            "login": LOGIN,
            "from": (now - timedelta(days=365)).isoformat(),
            "to": now.isoformat(),
        },
    )
    user = data["user"]

    days = []
    for week in user["contributionsCollection"]["contributionCalendar"]["weeks"]:
        for day in week["contributionDays"]:
            days.append(
                (datetime.fromisoformat(day["date"]).date(), day["contributionCount"])
            )
    days.sort()

    current, longest = compute_streaks(days)

    with open(README, encoding="utf-8") as handle:
        content = handle.read()

    content = replace(content, "snapshot", build_snapshot(user, days, current, longest))
    content = replace(content, "languages", build_languages(user))
    content = replace(content, "rhythm", build_rhythm(user, days))
    content = replace(
        content,
        "updated",
        f"_Last refreshed {datetime.now(IST):%d %B %Y, %H:%M} IST._",
    )

    with open(README, "w", encoding="utf-8") as handle:
        handle.write(content)

    print(f"README updated for {LOGIN}: streak {current}, longest {longest}")


if __name__ == "__main__":
    main()
