#!/usr/bin/env python3
"""GitHub GraphQL client and the shaping step that feeds every card.

One network module, two callers: the Vercel endpoint and the scheduled
workflow. Both get the same `ProfileData`, so a live card and a committed
fallback card can never disagree.

The commit history is fetched in a *single* batched query using GraphQL
aliases. The obvious implementation - one request per repository - took
about 30 seconds against this account, which exceeds Vercel's 10 second
function limit. See docs/superpowers/specs, constraint C3.
"""

import json
import os
import urllib.error
import urllib.request
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

API = "https://api.github.com/graphql"

# India has no daylight saving, so a fixed offset is exact and, unlike
# ZoneInfo("Asia/Kolkata"), needs no tzdata package on the host.
IST = timezone(timedelta(hours=5, minutes=30), "IST")

# How much history the rhythm clock samples. 30 repositories x 100 commits
# comfortably fits one request and one function invocation.
RHYTHM_REPOS = 30
RHYTHM_COMMITS = 100

WEEKDAYS = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]

WINDOWS = [
    ("Early morning", "05:00 - 09:00", list(range(5, 9))),
    ("Daytime", "09:00 - 17:00", list(range(9, 17))),
    ("Evening", "17:00 - 22:00", list(range(17, 22))),
    ("Late night", "22:00 - 05:00", list(range(22, 24)) + list(range(0, 5))),
]


class GitHubError(RuntimeError):
    """Raised for any failure to obtain usable data.

    Callers are expected to catch this and render a fallback card rather
    than return a non-2xx response: on a profile README a 500 shows up as
    a broken image icon.
    """


@dataclass
class ProfileData:
    login: str
    created_at: datetime
    followers: int
    total_contributions: int
    commits: int
    pull_requests: int
    issues: int
    reviews: int
    stars: int
    public_repos: int
    total_repos: int
    days: list = field(default_factory=list)      # [(date, count)] ascending
    languages: list = field(default_factory=list)  # [(name, share)] desc
    hours: dict = field(default_factory=dict)      # {hour: count} in IST
    commit_samples: int = 0
    repos: list = field(default_factory=list)      # raw repo nodes

    # -- derived ---------------------------------------------------------

    @property
    def current_streak(self):
        return self._streaks()[0]

    @property
    def longest_streak(self):
        return self._streaks()[1]

    def _streaks(self):
        longest = run = 0
        for _, count in self.days:
            run = run + 1 if count > 0 else 0
            longest = max(longest, run)

        current = 0
        today = datetime.now(IST).date()
        for date, count in reversed(self.days):
            if date > today:
                continue
            if count > 0:
                current += 1
            elif date == today:
                continue  # today may simply not have happened yet
            else:
                break
        return current, longest

    @property
    def busiest_day(self):
        """(date, count) of the single busiest day, or (None, 0)."""
        if not self.days:
            return None, 0
        return max(self.days, key=lambda d: d[1])

    @property
    def busiest_weekday(self):
        weekday = defaultdict(int)
        for date, count in self.days:
            weekday[date.weekday()] += count
        if not weekday:
            return None
        return WEEKDAYS[max(weekday.items(), key=lambda kv: kv[1])[0]]

    @property
    def peak_hour(self):
        if not self.commit_samples:
            return None
        return max(range(24), key=lambda h: self.hours.get(h, 0))

    @property
    def years_on_github(self):
        return (datetime.now(timezone.utc) - self.created_at).days / 365.25

    @property
    def weekly_totals(self):
        """Contributions bucketed into consecutive 7-day weeks, ascending."""
        weeks, bucket = [], []
        for date, count in self.days:
            bucket.append(count)
            if date.weekday() == 5:  # close the week on Saturday
                weeks.append(sum(bucket))
                bucket = []
        if bucket:
            weeks.append(sum(bucket))
        return weeks


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
        description
        url
        stargazerCount
        isPrivate
        pushedAt
        primaryLanguage { name }
        languages(first: 12, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name } }
        }
      }
    }
  }
}
"""


def _history_query(count):
    """Build one query with `count` aliased repository lookups.

    Repository names travel as GraphQL variables rather than being spliced
    into the query text, so an odd repository name cannot alter the query.
    """
    decls = ", ".join(f"$n{i}: String!" for i in range(count))
    blocks = "\n".join(
        f"""  r{i}: repository(owner: $login, name: $n{i}) {{
    defaultBranchRef {{ target {{ ... on Commit {{
      history(first: $count, author: {{id: $uid}}, since: $since) {{
        nodes {{ committedDate }}
      }} }} }} }}
  }}"""
        for i in range(count)
    )
    return (
        f"query($login: String!, $uid: ID!, $since: GitTimestamp!, "
        f"$count: Int!, {decls}) {{\n{blocks}\n}}"
    )


class Client:
    def __init__(self, token=None, login=None):
        self.token = (
            token
            or os.environ.get("GH_PAT")
            or os.environ.get("GH_TOKEN")
            or os.environ.get("GITHUB_TOKEN")
        )
        self.login = login or os.environ.get("GH_LOGIN", "Dhruv-413")
        if not self.token:
            raise GitHubError("No token: set GH_PAT, GH_TOKEN or GITHUB_TOKEN.")

    def query(self, document, variables):
        body = json.dumps({"query": document, "variables": variables}).encode()
        req = urllib.request.Request(
            API,
            data=body,
            headers={
                "Authorization": f"bearer {self.token}",
                "Content-Type": "application/json",
                "User-Agent": f"{self.login}-profile-readme",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                payload = json.loads(resp.read().decode())
        except urllib.error.HTTPError as exc:
            raise GitHubError(f"HTTP {exc.code}") from exc
        except Exception as exc:  # timeout, DNS, TLS
            raise GitHubError(str(exc)[:120]) from exc

        if "errors" in payload:
            first = payload["errors"][0].get("message", "unknown")
            raise GitHubError(f"GraphQL: {first[:120]}")
        if not payload.get("data"):
            raise GitHubError("GraphQL returned no data")
        return payload["data"]

    def fetch(self):
        now = datetime.now(timezone.utc)
        data = self.query(
            PROFILE_QUERY,
            {
                "login": self.login,
                "from": (now - timedelta(days=365)).isoformat(),
                "to": now.isoformat(),
            },
        )
        user = data.get("user")
        if not user:
            raise GitHubError(f"No such user: {self.login}")

        cc = user["contributionsCollection"]
        calendar = cc["contributionCalendar"]

        days = []
        for week in calendar["weeks"]:
            for day in week["contributionDays"]:
                days.append(
                    (
                        datetime.fromisoformat(day["date"]).date(),
                        day["contributionCount"],
                    )
                )
        days.sort()

        repos = user["repositories"]["nodes"]

        totals = defaultdict(int)
        for repo in repos:
            for edge in repo["languages"]["edges"]:
                totals[edge["node"]["name"]] += edge["size"]
        grand = sum(totals.values())
        languages = (
            [
                (name, size / grand)
                for name, size in sorted(
                    totals.items(), key=lambda kv: kv[1], reverse=True
                )[:6]
            ]
            if grand
            else []
        )

        hours, samples = self._commit_hours(user["id"], repos)

        return ProfileData(
            login=self.login,
            created_at=datetime.fromisoformat(user["createdAt"].replace("Z", "+00:00")),
            followers=user["followers"]["totalCount"],
            total_contributions=calendar["totalContributions"],
            commits=cc["totalCommitContributions"],
            pull_requests=cc["totalPullRequestContributions"],
            issues=cc["totalIssueContributions"],
            reviews=cc["totalPullRequestReviewContributions"],
            stars=sum(r["stargazerCount"] for r in repos),
            public_repos=sum(1 for r in repos if not r["isPrivate"]),
            total_repos=user["repositories"]["totalCount"],
            days=days,
            languages=languages,
            hours=hours,
            commit_samples=samples,
            repos=repos,
        )

    def _commit_hours(self, uid, repos):
        """Commit-hour histogram in IST, from one batched request."""
        names = [r["name"] for r in repos[:RHYTHM_REPOS]]
        if not names:
            return {}, 0

        variables = {
            "login": self.login,
            "uid": uid,
            "since": (datetime.now(timezone.utc) - timedelta(days=365)).isoformat(),
            "count": RHYTHM_COMMITS,
        }
        variables.update({f"n{i}": name for i, name in enumerate(names)})

        try:
            data = self.query(_history_query(len(names)), variables)
        except GitHubError:
            # The clock is a nicety; losing it should not lose the card set.
            return {}, 0

        hours = defaultdict(int)
        total = 0
        for i in range(len(names)):
            repo = data.get(f"r{i}")
            ref = (repo or {}).get("defaultBranchRef")
            if not ref or not ref.get("target"):
                continue
            for node in ref["target"].get("history", {}).get("nodes", []):
                stamp = datetime.fromisoformat(
                    node["committedDate"].replace("Z", "+00:00")
                )
                hours[stamp.astimezone(IST).hour] += 1
                total += 1
        return dict(hours), total
