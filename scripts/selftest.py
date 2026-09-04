#!/usr/bin/env python3
"""Renders every card in every theme from a fixture and checks the output.

Needs no token and touches no network, so it runs in CI on every push and
catches the failure this repository is most exposed to: an SVG that is
subtly malformed and renders as a broken image on the profile page, where
nobody sees an exception.

    python scripts/selftest.py
"""

import os
import random
import sys
import xml.dom.minidom
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from lib import cards  # noqa: E402
from lib.github import IST, ProfileData  # noqa: E402
from lib.theme import THEMES  # noqa: E402

# Values that mean a formatting bug reached the output.
POISON = ("None", "nan", "NaN", "Infinity", "{", "}")


def fixture():
    """A year of plausible history, deterministic so failures reproduce."""
    rng = random.Random(413)
    today = datetime.now(IST).date()
    days = []
    for offset in range(364, -1, -1):
        date = today - timedelta(days=offset)
        # Weekday-heavy, with quiet stretches, so streak logic gets exercised.
        base = 0 if rng.random() < 0.35 else rng.randint(1, 9)
        if date.weekday() >= 5:
            base = max(0, base - 3)
        days.append((date, base))

    repos = []
    for i, (name, lang) in enumerate(
        [
            ("alpha", "Python"),
            ("beta", "TypeScript"),
            ("gamma", "Jupyter Notebook"),
            ("delta", "JavaScript"),
            ("epsilon", "CSS"),
        ]
    ):
        repos.append(
            {
                "name": name,
                "description": f"Fixture repository {name}",
                "url": f"https://github.com/fixture/{name}",
                "stargazerCount": i,
                "isPrivate": i % 3 == 0,
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


def edge_cases():
    """A brand-new account: every aggregate is empty or zero.

    This is the shape that historically breaks chart code through
    division by zero or max() on an empty sequence.
    """
    empty = ProfileData(
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
    return {"empty account": empty}


def check(svg):
    """Assert the SVG is well formed and free of formatting accidents.

    minidom rather than defusedxml on purpose: the input is this
    process's own output, built moments earlier from escaped values,
    and it carries no DOCTYPE, so there is no entity to expand. Adding
    defusedxml would put a pip install in front of every workflow run
    for a threat this data cannot carry.
    """
    problems = []
    try:
        xml.dom.minidom.parseString(svg)
    except Exception as exc:
        problems.append(f"not well-formed XML: {exc}")

    if "viewBox" not in svg:
        problems.append("missing viewBox")
    if not svg.startswith("<svg") or not svg.rstrip().endswith("</svg>"):
        problems.append("missing svg envelope")
    if len(svg) < 400:
        problems.append(f"suspiciously short ({len(svg)} bytes)")
    for token in POISON:
        if token in svg:
            problems.append(f"contains {token!r}")
    return problems


def main():
    failures = 0
    checked = 0

    datasets = {"full year": fixture()}
    datasets.update(edge_cases())

    for label, data in datasets.items():
        for theme_name, theme in THEMES.items():
            for card_name, render in cards.CARDS.items():
                key = f"{card_name}/{theme_name} [{label}]"
                try:
                    svg = render(theme, data)
                except Exception as exc:
                    print(f"FAIL {key}: raised {type(exc).__name__}: {exc}")
                    failures += 1
                    continue
                problems = check(svg)
                checked += 1
                if problems:
                    failures += 1
                    for problem in problems:
                        print(f"FAIL {key}: {problem}")

    # The fallback card must survive too; it is what renders when all else
    # has already gone wrong.
    for theme_name, theme in THEMES.items():
        svg = cards.unavailable(THEMES[theme_name], "token expired")
        problems = check(svg)
        checked += 1
        if problems:
            failures += 1
            for problem in problems:
                print(f"FAIL unavailable/{theme_name}: {problem}")

    print(f"\n{checked} renders checked, {failures} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
