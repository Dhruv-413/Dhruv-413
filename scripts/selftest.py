#!/usr/bin/env python3
"""Renders every generated block from a fixture and checks the output.

Needs no token and touches no network, so it runs in CI on every push.
The failure it exists to catch is a block that renders as broken markdown
on the profile page, where there is no exception for anyone to see: an
unbalanced code fence swallows the rest of the file, and a table row with
the wrong column count silently drops a column.

    python scripts/selftest.py
"""

import os
import random
import re
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import build_readme as builder  # noqa: E402
from lib.github import IST, ProfileData  # noqa: E402

# Values that mean a formatting bug reached the output.
POISON = ("None", "nan", "NaN", "Infinity", "{", "}")


def fixture():
    """A year of plausible history, deterministic so failures reproduce."""
    rng = random.Random(413)
    today = datetime.now(IST).date()
    days = []
    for offset in range(364, -1, -1):
        date = today - timedelta(days=offset)
        # Weekday-heavy with quiet stretches, so streak logic gets exercised.
        base = 0 if rng.random() < 0.35 else rng.randint(1, 9)
        if date.weekday() >= 5:
            base = max(0, base - 3)
        days.append((date, base))

    repos = []
    for i, (name, lang) in enumerate(
        [
            ("StockAnalysis", "Python"),
            ("Dhruv", "TypeScript"),
            ("Basic-ML-Projects", "Jupyter Notebook"),
            ("EcoHive", "JavaScript"),
            ("private-thing", "CSS"),
        ]
    ):
        repos.append(
            {
                "name": name,
                "description": f"Fixture repository {name}",
                "url": f"https://github.com/fixture/{name}",
                "stargazerCount": i,
                "isPrivate": name == "private-thing",
                "pushedAt": "2026-08-01T00:00:00Z",
                "primaryLanguage": {"name": lang},
                "languages": {
                    "edges": [{"size": 1000 * (i + 1), "node": {"name": lang}}]
                },
            }
        )

    return ProfileData(
        login="fixture-user",
        created_at=datetime.now(timezone.utc) - timedelta(days=1000),
        followers=12,
        total_contributions=sum(c for _, c in days),
        commits=430,
        pull_requests=17,
        issues=5,
        reviews=3,
        stars=10,
        public_repos=4,
        total_repos=5,
        days=days,
        languages=[
            ("Python", 0.44),
            ("TypeScript", 0.27),
            ("Jupyter Notebook", 0.19),
            ("JavaScript", 0.06),
            ("CSS", 0.03),
            ("HTML", 0.01),
        ],
        hours={h: rng.randint(0, 20) for h in range(24)},
        commit_samples=240,
        repos=repos,
    )


def empty_account():
    """A brand-new account: every aggregate is empty or zero.

    This is the shape that breaks chart code through division by zero or
    max() on an empty sequence.
    """
    return ProfileData(
        login="empty-user",
        created_at=datetime.now(timezone.utc) - timedelta(days=3),
        followers=0,
        total_contributions=0,
        commits=0,
        pull_requests=0,
        issues=0,
        reviews=0,
        stars=0,
        public_repos=0,
        total_repos=0,
        days=[(datetime.now(IST).date(), 0)],
        languages=[],
        hours={},
        commit_samples=0,
        repos=[],
    )


def check(text):
    problems = []

    if not text or not text.strip():
        problems.append("empty output")

    for token in POISON:
        if token in text:
            problems.append(f"contains {token!r}")

    # An unbalanced fence swallows the remainder of the README.
    if text.count("```") % 2:
        problems.append("unbalanced code fence")

    # Every row of a markdown table needs the same column count, or GitHub
    # quietly drops cells.
    rows = [
        line for line in text.splitlines()
        if line.startswith("|") and not re.fullmatch(r"[|:\- ]+", line)
    ]
    if rows:
        widths = {line.count("|") for line in rows}
        if len(widths) > 1:
            problems.append(f"ragged table columns: {sorted(widths)}")

    # A table needs its delimiter row or it renders as literal pipes.
    if rows and not any(re.fullmatch(r"[|:\- ]+", line) for line in text.splitlines()):
        problems.append("table without a delimiter row")

    return problems


def main():
    failures = 0
    checked = 0

    for label, data in (("full year", fixture()), ("empty account", empty_account())):
        for marker, build in builder.BLOCKS.items():
            key = f"{marker} [{label}]"
            try:
                text = build(data)
            except Exception as exc:
                print(f"FAIL {key}: raised {type(exc).__name__}: {exc}")
                failures += 1
                continue
            checked += 1
            for problem in check(text):
                print(f"FAIL {key}: {problem}")
                failures += 1

    # The contribution grid must stay rectangular, or the columns shear.
    grid = builder.build_grid(fixture())
    body = [
        line for line in grid.splitlines()
        if line and not line.startswith("```") and not line.strip().startswith("less")
    ]
    lengths = {len(line) for line in body}
    checked += 1
    if len(lengths) > 1:
        print(f"FAIL grid: rows differ in width: {sorted(lengths)}")
        failures += 1

    # Axis labels must land on the tick they name. This drifted once
    # already: the final label overhung the row and "23" rendered as "2".
    axis = builder._ticks(24, {0: "00", 6: "06", 12: "12", 18: "18", 23: "23"})
    checked += 1
    for tick, want in (("00", 0), ("06", 6), ("12", 12), ("18", 18), ("23", 23)):
        if tick not in axis:
            print(f"FAIL axis: label {tick!r} missing, probably clipped")
            failures += 1
        elif axis.index(tick) != want:
            print(f"FAIL axis: {tick!r} at {axis.index(tick)}, expected {want}")
            failures += 1

    print(f"\n{checked} blocks checked, {failures} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
