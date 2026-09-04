#!/usr/bin/env python3
"""Vercel function that renders one statistics card on request.

    /api/card?card=contributions&theme=dark

Design notes worth keeping in view when editing:

  * It never returns a non-2xx. A 500 renders as a broken image icon on a
    profile page, where nobody is watching logs. Every failure path falls
    through to `cards.unavailable`, drawn in the same visual language, at
    HTTP 200.

  * Caching is done by Vercel's CDN, not by this function, which is
    stateless. `s-maxage=1800` means at most a couple of GraphQL calls an
    hour per card against a 5,000/hour limit, and
    `stale-while-revalidate` means a rate-limited or slow API shows the
    last good card instead of nothing.

  * The token is read from the environment and is never logged, echoed,
    or embedded in the SVG.
"""

import os
import sys
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from lib import cards  # noqa: E402
from lib.github import Client, GitHubError  # noqa: E402
from lib.theme import THEMES  # noqa: E402

# 30 minutes fresh at the edge, then a day of serving stale while a fresh
# copy is fetched in the background.
CACHE = "public, max-age=0, s-maxage=1800, stale-while-revalidate=86400"

DEFAULT_CARD = "snapshot"
DEFAULT_THEME = "light"


def render(query):
    """Return (svg, cache_header). Never raises."""
    params = parse_qs(query)
    name = (params.get("card") or [DEFAULT_CARD])[0]
    theme_name = (params.get("theme") or [DEFAULT_THEME])[0]

    # Unknown values fall back rather than erroring: a typo in the README
    # should still render something sensible.
    theme = THEMES.get(theme_name, THEMES[DEFAULT_THEME])
    draw = cards.CARDS.get(name)
    if draw is None:
        draw = cards.CARDS[DEFAULT_CARD]

    try:
        data = Client().fetch()
    except GitHubError as exc:
        # Do not cache a failure for the full window; retry sooner.
        return cards.unavailable(theme, str(exc)), "public, max-age=0, s-maxage=60"
    except Exception:  # noqa: BLE001 - last line of defence
        return (
            cards.unavailable(theme, "unexpected error"),
            "public, max-age=0, s-maxage=60",
        )

    try:
        return draw(theme, data), CACHE
    except Exception:  # noqa: BLE001 - a drawing bug must not break the page
        return (
            cards.unavailable(theme, "could not draw this card"),
            "public, max-age=0, s-maxage=60",
        )


class handler(BaseHTTPRequestHandler):  # noqa: N801 - Vercel requires this name
    def do_GET(self):  # noqa: N802 - BaseHTTPRequestHandler's interface
        svg, cache = render(urlparse(self.path).query)
        body = svg.encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "image/svg+xml; charset=utf-8")
        self.send_header("Cache-Control", cache)
        self.send_header("Content-Length", str(len(body)))
        # The SVG is rendered by the browser in secure-static mode anyway;
        # this makes that explicit to any intermediary.
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)
