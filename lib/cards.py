#!/usr/bin/env python3
"""Every statistics card, drawn from scratch.

These functions are pure: shaped data in, SVG string out. No network, no
filesystem, no clock. That is what lets the Vercel endpoint and the
scheduled workflow render byte-identical output, and what lets the self
test run without a token.

Why render our own rather than embed a trophy service or an activity
graph service: five widgets from five services means five palettes, five
type stacks and five corner radii. Six charts from one palette read as a
dashboard. See the spec, section 5.
"""

import math

from .theme import MONO, SANS, esc, grain_filter, open_svg

W = 1200
PAD = 72


# --------------------------------------------------------------------------
# Shared chrome
# --------------------------------------------------------------------------


def shell(t, height):
    """Card background: fill, sheen, grain, then the outer hairline."""
    return (
        "<defs>"
        + grain_filter(t)
        + '<linearGradient id="depth" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0%" stop-color="#FFFFFF" stop-opacity="{t["depth_op"]}"/>'
        '<stop offset="65%" stop-color="#FFFFFF" stop-opacity="0"/>'
        "</linearGradient>"
        f'<clipPath id="shell"><rect width="{W}" height="{height}" rx="22"/></clipPath>'
        "</defs>"
        '<g clip-path="url(#shell)">'
        f'<rect width="{W}" height="{height}" fill="{t["bg"]}"/>'
        f'<rect width="{W}" height="{height}" fill="url(#depth)"/>'
        f'<rect width="{W}" height="{height}" filter="url(#grain)" '
        f'opacity="{t["grain_op"]}"/>'
        "</g>"
        f'<rect x="0.75" y="0.75" width="{W - 1.5}" height="{height - 1.5}" '
        f'rx="21.25" fill="none" stroke="{t["hairline"]}" '
        f'stroke-opacity="{t["ring_op"]}" stroke-width="1.5"/>'
    )


def header(t, eyebrow, title, subtitle=None):
    out = [
        f'<text x="{PAD}" y="70" font-family="{MONO}" font-size="12" '
        f'font-weight="500" letter-spacing="3.4" fill="{t["accent"]}">'
        f"{esc(eyebrow)}</text>",
        f'<text x="{PAD - 2}" y="118" font-family="{SANS}" font-size="30" '
        f'font-weight="600" letter-spacing="-0.9" fill="{t["text"]}">'
        f"{esc(title)}</text>",
    ]
    if subtitle:
        out.append(
            f'<text x="{PAD}" y="147" font-family="{SANS}" font-size="14.5" '
            f'fill="{t["muted"]}">{esc(subtitle)}</text>'
        )
    return "".join(out)


def _num(value):
    return f"{value:,}"


# --------------------------------------------------------------------------
# snapshot
# --------------------------------------------------------------------------


def snapshot(t, d):
    """Headline figures as a stat bar, separated by hairlines."""
    height = 300
    figures = [
        (_num(d.total_contributions), "Contributions", "last 12 months"),
        (_num(d.commits), "Commits", "authored"),
        (_num(d.pull_requests), "Pull requests", "opened"),
        (_num(d.public_repos), "Repositories", "public"),
        (_num(d.stars), "Stars", "earned"),
    ]

    parts = [
        open_svg(W, height, f"{d.total_contributions} contributions in the last year"),
        shell(t, height),
        header(
            t,
            "SNAPSHOT",
            "The last twelve months",
            f"Live from the GitHub GraphQL API  ·  {d.login}",
        ),
    ]

    inner = W - 2 * PAD
    step = inner / len(figures)
    for i, (value, label, sub) in enumerate(figures):
        x = PAD + i * step
        if i:
            parts.append(
                f'<line x1="{x - 18:.1f}" y1="196" x2="{x - 18:.1f}" y2="262" '
                f'stroke="{t["hairline"]}" stroke-opacity="{t["hairline_op"]}"/>'
            )
        parts.append(
            f'<text x="{x:.1f}" y="234" font-family="{SANS}" font-size="42" '
            f'font-weight="600" letter-spacing="-1.6" fill="{t["text"]}">'
            f"{esc(value)}</text>"
            f'<text x="{x:.1f}" y="258" font-family="{SANS}" font-size="14" '
            f'font-weight="500" fill="{t["muted"]}">{esc(label)}</text>'
            f'<text x="{x:.1f}" y="277" font-family="{MONO}" font-size="11" '
            f'letter-spacing="0.6" fill="{t["faint"]}">{esc(sub)}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


# --------------------------------------------------------------------------
# contributions
# --------------------------------------------------------------------------


def _level(count, busiest):
    """Map a day's count onto the five-step intensity ramp."""
    if count <= 0:
        return 0
    if busiest <= 1:
        return 4
    ratio = count / busiest
    if ratio <= 0.25:
        return 1
    if ratio <= 0.50:
        return 2
    if ratio <= 0.75:
        return 3
    return 4


def contributions(t, d):
    """The 53-week heatmap."""
    height = 400
    x0, y0 = PAD + 34, 200
    step, cell = 19.3, 15.0
    days = d.days
    busiest_count = max((c for _, c in days), default=0)
    current, longest = d.current_streak, d.longest_streak

    parts = [
        open_svg(W, height, f"{d.total_contributions} contributions in the last year"),
        shell(t, height),
        header(
            t,
            "CONTRIBUTION GRAPH",
            f"{_num(d.total_contributions)} contributions in the last year",
            f"Current streak {current} day{'s' if current != 1 else ''}"
            f"  ·  longest {longest} days"
            f"  ·  busiest day {busiest_count} contributions",
        ),
    ]

    # Columns are weeks; the first column starts on the calendar's own week
    # boundary so the weekday rows stay aligned all the way across.
    weeks, week = [], []
    for date, count in days:
        if date.weekday() == 6 and week:  # Sunday opens a new column
            weeks.append(week)
            week = []
        week.append((date, count))
    if week:
        weeks.append(week)
    weeks = weeks[-53:]

    seen_month = set()
    for col, wk in enumerate(weeks):
        cx = x0 + col * step
        for date, count in wk:
            row = (date.weekday() + 1) % 7  # Sunday first, like GitHub
            cy = y0 + row * step
            parts.append(
                f'<rect x="{cx:.1f}" y="{cy:.1f}" width="{cell}" height="{cell}" '
                f'rx="3.6" fill="{t["scale"][_level(count, busiest_count)]}"/>'
            )
        first = wk[0][0]
        if first.month not in seen_month and first.day <= 8:
            seen_month.add(first.month)
            parts.append(
                f'<text x="{cx:.1f}" y="{y0 - 14}" font-family="{MONO}" '
                f'font-size="11.5" letter-spacing="1.2" fill="{t["faint"]}">'
                f"{first:%b}</text>"
            )

    for row, name in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        parts.append(
            f'<text x="{PAD}" y="{y0 + row * step + 11.5:.1f}" '
            f'font-family="{MONO}" font-size="11" fill="{t["faint"]}">{name}</text>'
        )

    ly = y0 + 7 * step + 30
    lx = W - PAD - 5 * 19 - 74
    parts.append(
        f'<text x="{lx - 10}" y="{ly + 11}" font-family="{MONO}" font-size="11" '
        f'text-anchor="end" fill="{t["faint"]}">Less</text>'
    )
    for i, colour in enumerate(t["scale"]):
        parts.append(
            f'<rect x="{lx + i * 19}" y="{ly}" width="14" height="14" rx="3.4" '
            f'fill="{colour}"/>'
        )
    parts.append(
        f'<text x="{lx + 5 * 19 + 2}" y="{ly + 11}" font-family="{MONO}" '
        f'font-size="11" fill="{t["faint"]}">More</text>'
    )
    parts.append("</svg>")
    return "".join(parts)


# --------------------------------------------------------------------------
# activity
# --------------------------------------------------------------------------


def activity(t, d):
    """Contribution trend across the year, as an area chart."""
    height = 390
    weeks = d.weekly_totals
    parts = [
        open_svg(W, height, "Contribution trend over the last year"),
        shell(t, height),
        header(
            t,
            "ACTIVITY TREND",
            "Contributions per week",
            "Every week of the last year, so streaks and gaps both show.",
        ),
    ]

    if len(weeks) < 2:
        parts.append(
            f'<text x="{PAD}" y="250" font-family="{SANS}" font-size="16" '
            f'fill="{t["muted"]}">Not enough history to plot.</text></svg>'
        )
        return "".join(parts)

    left, right = PAD + 26, W - PAD
    top, base = 192, 316
    peak = max(weeks) or 1
    span = right - left
    dx = span / (len(weeks) - 1)

    def point(i, value):
        return left + i * dx, base - (base - top) * (value / peak)

    coords = [point(i, v) for i, v in enumerate(weeks)]

    # Horizontal guides at 0, half and peak.
    for frac in (0, 0.5, 1.0):
        y = base - (base - top) * frac
        parts.append(
            f'<line x1="{left}" y1="{y:.1f}" x2="{right}" y2="{y:.1f}" '
            f'stroke="{t["hairline"]}" stroke-opacity="{t["hairline_op"]}"/>'
            f'<text x="{PAD - 12}" y="{y + 4:.1f}" font-family="{MONO}" '
            f'font-size="11" text-anchor="end" fill="{t["faint"]}">'
            f"{int(round(peak * frac))}</text>"
        )

    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in coords)
    area = (
        f"{left:.1f},{base} "
        + line
        + f" {right:.1f},{base}"
    )
    parts.append(
        f'<linearGradient id="fill" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0%" stop-color="{t["accent"]}" stop-opacity="0.42"/>'
        f'<stop offset="100%" stop-color="{t["accent"]}" stop-opacity="0.02"/>'
        f"</linearGradient>"
        f'<polygon points="{area}" fill="url(#fill)"/>'
        f'<polyline points="{line}" fill="none" stroke="{t["accent"]}" '
        f'stroke-width="2.2" stroke-linejoin="round" stroke-linecap="round"/>'
    )

    # Mark the best week.
    best = max(range(len(weeks)), key=lambda i: weeks[i])
    bx, by = coords[best]
    parts.append(
        f'<circle cx="{bx:.1f}" cy="{by:.1f}" r="5" fill="{t["mint"]}"/>'
        f'<circle cx="{bx:.1f}" cy="{by:.1f}" r="10" fill="none" '
        f'stroke="{t["mint"]}" stroke-opacity="0.4"/>'
        f'<text x="{bx:.1f}" y="{by - 20:.1f}" font-family="{MONO}" '
        f'font-size="12" text-anchor="middle" fill="{t["mint"]}">'
        f"{weeks[best]}</text>"
    )

    # Month ticks along the baseline.
    if d.days:
        seen = set()
        for i, (date, _) in enumerate(d.days):
            if date.day <= 7 and date.month not in seen:
                seen.add(date.month)
                x = left + (i / 7) * dx
                if left <= x <= right:
                    parts.append(
                        f'<text x="{x:.1f}" y="{base + 26}" font-family="{MONO}" '
                        f'font-size="11.5" letter-spacing="1.2" '
                        f'text-anchor="middle" fill="{t["faint"]}">{date:%b}</text>'
                    )
    parts.append("</svg>")
    return "".join(parts)


# --------------------------------------------------------------------------
# languages
# --------------------------------------------------------------------------


def languages(t, d):
    height = 330
    langs = d.languages
    parts = [
        open_svg(W, height, "Language footprint"),
        shell(t, height),
        header(
            t,
            "LANGUAGE FOOTPRINT",
            "Where the code actually goes",
            "By bytes committed across every source repository I own.",
        ),
    ]

    if not langs:
        parts.append(
            f'<text x="{PAD}" y="230" font-family="{SANS}" font-size="16" '
            f'fill="{t["muted"]}">No language data available.</text></svg>'
        )
        return "".join(parts)

    # One stacked bar. Segments are clipped to a rounded rect so the ends
    # stay round without faking a cap on each segment.
    bar_w, bar_y, bar_h = W - 2 * PAD, 182, 22
    parts.append(
        f'<clipPath id="barclip"><rect x="{PAD}" y="{bar_y}" width="{bar_w}" '
        f'height="{bar_h}" rx="{bar_h / 2}"/></clipPath>'
        f'<rect x="{PAD}" y="{bar_y}" width="{bar_w}" height="{bar_h}" '
        f'rx="{bar_h / 2}" fill="{t["track"]}"/>'
        '<g clip-path="url(#barclip)">'
    )
    cursor = float(PAD)
    covered = sum(share for _, share in langs)
    for i, (_, share) in enumerate(langs):
        seg = bar_w * share / covered
        parts.append(
            f'<rect x="{cursor:.2f}" y="{bar_y}" width="{seg + 1:.2f}" '
            f'height="{bar_h}" fill="{t["series"][i % len(t["series"])]}"/>'
        )
        cursor += seg
    parts.append("</g>")

    col_x = [PAD, PAD + 540]
    for i, (name, share) in enumerate(langs):
        x = col_x[i % 2]
        y = 254 + (i // 2) * 34
        colour = t["series"][i % len(t["series"])]
        parts.append(
            f'<circle cx="{x + 5}" cy="{y - 5}" r="5" fill="{colour}"/>'
            f'<text x="{x + 20}" y="{y}" font-family="{SANS}" font-size="15" '
            f'font-weight="500" fill="{t["text"]}">{esc(name)}</text>'
            f'<text x="{x + 460}" y="{y}" font-family="{MONO}" font-size="14" '
            f'text-anchor="end" fill="{t["muted"]}">{share * 100:.1f}%</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


# --------------------------------------------------------------------------
# rhythm
# --------------------------------------------------------------------------

WINDOWS = [
    ("Early morning", "05:00 - 09:00", list(range(5, 9))),
    ("Daytime", "09:00 - 17:00", list(range(9, 17))),
    ("Evening", "17:00 - 22:00", list(range(17, 22))),
    ("Late night", "22:00 - 05:00", list(range(22, 24)) + list(range(0, 5))),
]


def rhythm(t, d):
    """A 24-hour dial in IST, plus the four windows as bars."""
    height = 440
    hours = d.hours
    total = d.commit_samples
    parts = [
        open_svg(W, height, "Commit rhythm by hour of day, IST"),
        shell(t, height),
        header(
            t,
            "COMMIT RHYTHM  ·  IST (UTC+05:30)",
            "When I actually commit",
            f"Hour of day for {_num(total)} commit timestamps, converted to IST."
            if total
            else "No commit timestamps available.",
        ),
    ]

    if not total:
        parts.append("</svg>")
        return "".join(parts)

    cx, cy = 262, 272
    r_in, r_out = 52, 138
    peak_hour = d.peak_hour
    peak = hours.get(peak_hour, 0)

    for r in (r_in, r_out):
        parts.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" '
            f'stroke="{t["hairline"]}" stroke-opacity="{t["hairline_op"]}"/>'
        )

    for h in range(24):
        count = hours.get(h, 0)
        share = count / peak if peak else 0
        length = r_in + (r_out - r_in) * share
        angle = math.radians(h * 15 - 90)
        x1, y1 = cx + r_in * math.cos(angle), cy + r_in * math.sin(angle)
        x2, y2 = cx + length * math.cos(angle), cy + length * math.sin(angle)
        opacity = "0.95" if h == peak_hour else ("0.62" if count else "0.12")
        stroke = t["mint"] if h == peak_hour else (t["accent"] if count else t["hairline"])
        parts.append(
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{stroke}" stroke-opacity="{opacity}" stroke-width="9" '
            f'stroke-linecap="round"/>'
        )

    for h, tick in ((0, "00"), (6, "06"), (12, "12"), (18, "18")):
        angle = math.radians(h * 15 - 90)
        tx = cx + (r_out + 22) * math.cos(angle)
        ty = cy + (r_out + 22) * math.sin(angle)
        parts.append(
            f'<text x="{tx:.1f}" y="{ty + 4.5:.1f}" font-family="{MONO}" '
            f'font-size="13" letter-spacing="0.8" text-anchor="middle" '
            f'fill="{t["muted"]}">{tick}</text>'
        )

    parts.append(
        f'<text x="{cx}" y="{cy - 2}" font-family="{SANS}" font-size="27" '
        f'font-weight="600" text-anchor="middle" fill="{t["text"]}">'
        f"{peak_hour:02d}:00</text>"
        f'<text x="{cx}" y="{cy + 20}" font-family="{MONO}" font-size="10.5" '
        f'letter-spacing="2.2" text-anchor="middle" fill="{t["faint"]}">PEAK HOUR</text>'
    )

    bx, bw = 520, 540
    for i, (name, window, span) in enumerate(WINDOWS):
        count = sum(hours.get(h, 0) for h in span)
        share = count / total
        y = 196 + i * 52
        parts.append(
            f'<text x="{bx}" y="{y}" font-family="{SANS}" font-size="15" '
            f'font-weight="500" fill="{t["text"]}">{esc(name)}</text>'
            f'<text x="{bx + 150}" y="{y}" font-family="{MONO}" font-size="12" '
            f'fill="{t["faint"]}">{window}</text>'
            f'<text x="{bx + bw}" y="{y}" font-family="{MONO}" font-size="13" '
            f'text-anchor="end" fill="{t["muted"]}">{share * 100:.0f}%</text>'
            f'<rect x="{bx}" y="{y + 10}" width="{bw}" height="8" rx="4" '
            f'fill="{t["track"]}"/>'
            f'<rect x="{bx}" y="{y + 10}" width="{max(bw * share, 4):.1f}" '
            f'height="8" rx="4" fill="{t["series"][i]}"/>'
        )

    if d.busiest_weekday:
        parts.append(
            f'<text x="{bx}" y="405" font-family="{SANS}" font-size="14" '
            f'fill="{t["muted"]}">Most active day of the week: '
            f'<tspan font-weight="600" fill="{t["text"]}">'
            f"{esc(d.busiest_weekday)}</tspan></text>"
        )
    parts.append("</svg>")
    return "".join(parts)


# --------------------------------------------------------------------------
# milestones
# --------------------------------------------------------------------------


def milestones(t, d):
    """What a trophy wall would show, if the trophies were real.

    Deliberately not `github-profile-trophy`: that service is theme-based
    rather than per-colour, so it cannot match this palette without
    forking it, and generic trophies rank low on a young account anyway.
    Every figure here is computed from this account's own history.
    """
    height = 340
    busiest_date, busiest_count = d.busiest_day
    distinct_languages = len(
        {
            edge["node"]["name"]
            for repo in d.repos
            for edge in repo["languages"]["edges"]
        }
    )

    tiles = [
        (_num(d.longest_streak), "Longest streak", "consecutive days"),
        (
            _num(busiest_count),
            "Busiest day",
            f"{busiest_date:%d %b %Y}" if busiest_date else "no data",
        ),
        (_num(distinct_languages), "Languages", "shipped in public repos"),
        (f"{d.years_on_github:.1f}", "Years", "on GitHub"),
        (_num(d.total_repos), "Repositories", "owned, excluding forks"),
    ]

    parts = [
        open_svg(W, height, "Milestones computed from this account's history"),
        shell(t, height),
        header(
            t,
            "MILESTONES",
            "Earned, not awarded",
            "Every figure below is computed from this account's own history.",
        ),
    ]

    inner = W - 2 * PAD
    gap = 20
    tile_w = (inner - gap * (len(tiles) - 1)) / len(tiles)
    for i, (value, label, sub) in enumerate(tiles):
        x = PAD + i * (tile_w + gap)
        colour = t["series"][i % len(t["series"])]
        parts.append(
            f'<rect x="{x:.1f}" y="188" width="{tile_w:.1f}" height="112" rx="16" '
            f'fill="{t["raise"]}" stroke="{t["hairline"]}" '
            f'stroke-opacity="{t["hairline_op"]}"/>'
            f'<rect x="{x + 20:.1f}" y="188" width="40" height="3" rx="1.5" '
            f'fill="{colour}"/>'
            f'<text x="{x + 20:.1f}" y="245" font-family="{SANS}" font-size="34" '
            f'font-weight="600" letter-spacing="-1.2" fill="{t["text"]}">'
            f"{esc(value)}</text>"
            f'<text x="{x + 20:.1f}" y="268" font-family="{SANS}" font-size="13.5" '
            f'font-weight="500" fill="{t["muted"]}">{esc(label)}</text>'
            f'<text x="{x + 20:.1f}" y="286" font-family="{MONO}" font-size="10.5" '
            f'fill="{t["faint"]}">{esc(sub)}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


# --------------------------------------------------------------------------
# fallback
# --------------------------------------------------------------------------


def unavailable(t, reason="stats temporarily unavailable"):
    """Shown instead of an error.

    A non-2xx response renders as a broken image icon on a profile page,
    which is the worst failure this page has. So every error path lands
    here, with HTTP 200.
    """
    height = 220
    return "".join(
        [
            open_svg(W, height, f"Statistics unavailable: {reason}"),
            shell(t, height),
            header(t, "SNAPSHOT", "Statistics are catching up", esc(reason)),
            f'<text x="{PAD}" y="182" font-family="{MONO}" font-size="12.5" '
            f'fill="{t["faint"]}">The scheduled build will restore this shortly.'
            f"</text>",
            "</svg>",
        ]
    )


CARDS = {
    "snapshot": snapshot,
    "contributions": contributions,
    "activity": activity,
    "languages": languages,
    "rhythm": rhythm,
    "milestones": milestones,
}
