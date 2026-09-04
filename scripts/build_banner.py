#!/usr/bin/env python3
"""Generates the README hero banner in both themes.

The motif on the right is a small vector space: a scattered point cloud,
one query node, and the links to its nearest neighbours. It is the same
picture as the work described underneath it, which is the only reason it
is there. Positions come from a fixed seed so the two themes line up
exactly and reruns produce no diff.

Output: assets/banner-dark.svg, assets/banner-light.svg
"""

import math
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from lib.theme import (
    MONO,
    SANS,
    THEMES,
    esc,
    grain_filter,
    open_svg,
    write,
)  # noqa: E402

W, H = 1200, 340
ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")

NAME = "Dhruv Gupta"
EYEBROW = "FULL-STACK ENGINEER / AI SYSTEMS"
ROLE = "I build retrieval, vision and data systems."
DETAIL = "Semantic search  ·  Computer vision  ·  Enterprise data modernization"
STATUS = "Ghaziabad, India  ·  IST (UTC+5:30)  ·  open to collaboration"

# Centre sits far enough right that the cloud runs off the card edge. A
# window onto a bigger space reads better than a specimen in a jar.
CX, CY = 992, 168
CLOUD_R = 192
SEED = 413  # from the handle, and it keeps the cloud stable


def point_cloud(count=76, min_gap=21):
    """Rejection-sampled points in an ellipse: even, but not a grid."""
    rng = random.Random(SEED)
    points = []
    guard = 0
    while len(points) < count and guard < 20000:
        guard += 1
        angle = rng.uniform(0, math.tau)
        radius = CLOUD_R * math.sqrt(rng.random())
        x = CX + radius * math.cos(angle) * 1.18
        y = CY + radius * math.sin(angle) * 0.92
        if all((x - px) ** 2 + (y - py) ** 2 > min_gap**2 for px, py in points):
            points.append((x, y))
    return points


def motif(t):
    """Point cloud, query node, and its k nearest neighbours."""
    points = point_cloud()
    query = min(points, key=lambda p: (p[0] - CX) ** 2 + (p[1] - CY) ** 2)
    others = [p for p in points if p != query]
    neighbours = sorted(
        others,
        key=lambda p: (p[0] - query[0]) ** 2 + (p[1] - query[1]) ** 2,
    )[:6]
    neighbour_set = set(neighbours)

    out = ['<g mask="url(#fade)">']

    # Ambient points first, so the highlighted set always sits on top.
    # Size and opacity jitter keeps the cloud from reading as a texture swatch.
    jitter = random.Random(SEED + 1)
    for x, y in others:
        if (x, y) in neighbour_set:
            continue
        out.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{jitter.uniform(1.8, 3.2):.1f}" '
            f'fill="{t["muted"]}" fill-opacity="{jitter.uniform(0.24, 0.52):.2f}"/>'
        )

    # Links, drawn as a dashed path that drifts toward the query node.
    for i, (x, y) in enumerate(neighbours):
        length = math.hypot(x - query[0], y - query[1])
        out.append(
            f'<line x1="{query[0]:.1f}" y1="{query[1]:.1f}" '
            f'x2="{x:.1f}" y2="{y:.1f}" stroke="{t["accent"]}" '
            f'stroke-opacity="0.55" stroke-width="1.1" '
            f'stroke-dasharray="3 6" stroke-linecap="round">'
            f'<animate attributeName="stroke-dashoffset" '
            f'values="{length:.0f};0" dur="{5.5 + i * 0.45:.2f}s" '
            f'repeatCount="indefinite"/></line>'
        )

    for x, y in neighbours:
        out.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{t["accent_2"]}" '
            f'fill-opacity="0.95"/>'
        )

    qx, qy = query
    out.append(
        f'<circle cx="{qx:.1f}" cy="{qy:.1f}" r="9" fill="none" '
        f'stroke="{t["mint"]}" stroke-opacity="0.55" stroke-width="1.2">'
        f'<animate attributeName="r" values="9;19;9" dur="4.6s" '
        f'repeatCount="indefinite"/>'
        f'<animate attributeName="stroke-opacity" values="0.55;0;0.55" '
        f'dur="4.6s" repeatCount="indefinite"/></circle>'
        f'<circle cx="{qx:.1f}" cy="{qy:.1f}" r="5.5" fill="{t["mint"]}"/>'
    )
    out.append("</g>")
    return "".join(out)


def build(t):
    accent, text, muted = t["accent"], t["text"], t["muted"]
    parts = [open_svg(W, H, f"{NAME} — full-stack engineer and AI systems developer")]

    parts.append("<defs>")
    parts.append(grain_filter(t))
    parts.append(
        f'<radialGradient id="glow" cx="0.5" cy="0.5" r="0.5">'
        f'<stop offset="0%" stop-color="{accent}" stop-opacity="{t["glow_op"]}"/>'
        f'<stop offset="100%" stop-color="{accent}" stop-opacity="0"/>'
        f"</radialGradient>"
    )
    # The motif fades out toward the type so the two never fight.
    parts.append(
        '<linearGradient id="fadeGrad" x1="0" y1="0" x2="1" y2="0">'
        '<stop offset="0%" stop-color="#000000"/>'
        '<stop offset="50%" stop-color="#444444"/>'
        '<stop offset="74%" stop-color="#ffffff"/>'
        "</linearGradient>"
        f'<mask id="fade"><rect width="{W}" height="{H}" fill="url(#fadeGrad)"/></mask>'
    )
    parts.append(
        f'<linearGradient id="rule" x1="0" y1="0" x2="1" y2="0">'
        f'<stop offset="0%" stop-color="{accent}"/>'
        f'<stop offset="100%" stop-color="{accent}" stop-opacity="0"/>'
        f"</linearGradient>"
    )
    parts.append(
        f'<pattern id="grid" width="44" height="44" patternUnits="userSpaceOnUse">'
        f'<path d="M44 0H0V44" fill="none" stroke="{t["hairline"]}" '
        f'stroke-opacity="{t["hairline_op"]}" stroke-width="1"/>'
        f"</pattern>"
    )
    # A sheen down the top of the card. Flat fills read as cheap.
    parts.append(
        f'<linearGradient id="depth" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0%" stop-color="#FFFFFF" stop-opacity="{t["depth_op"]}"/>'
        f'<stop offset="60%" stop-color="#FFFFFF" stop-opacity="0"/>'
        f"</linearGradient>"
    )
    parts.append(
        f'<clipPath id="shell"><rect width="{W}" height="{H}" rx="22"/></clipPath>'
    )
    parts.append("</defs>")

    parts.append('<g clip-path="url(#shell)">')
    parts.append(f'<rect width="{W}" height="{H}" rx="22" fill="{t["bg"]}"/>')
    parts.append(f'<rect width="{W}" height="{H}" fill="url(#depth)"/>')
    parts.append(
        f'<rect width="{W}" height="{H}" fill="url(#grid)" mask="url(#fade)"/>'
    )
    parts.append(
        f'<ellipse cx="{CX}" cy="{CY - 40}" rx="380" ry="270" fill="url(#glow)"/>'
    )
    parts.append(motif(t))
    parts.append(
        f'<rect width="{W}" height="{H}" filter="url(#grain)" '
        f'opacity="{t["grain_op"]}"/>'
    )
    parts.append("</g>")

    # Type column.
    x = 72
    parts.append(
        f'<text x="{x}" y="96" font-family="{MONO}" font-size="12.5" '
        f'font-weight="500" letter-spacing="3.6" fill="{accent}">{esc(EYEBROW)}</text>'
    )
    parts.append(
        f'<text x="{x - 3}" y="166" font-family="{SANS}" font-size="64" '
        f'font-weight="600" letter-spacing="-2.2" fill="{text}">{esc(NAME)}</text>'
    )
    parts.append(
        f'<rect x="{x}" y="186" width="118" height="2" rx="1" fill="url(#rule)"/>'
    )
    parts.append(
        f'<text x="{x}" y="222" font-family="{SANS}" font-size="18.5" '
        f'font-weight="450" fill="{muted}">{esc(ROLE)}</text>'
    )
    parts.append(
        f'<text x="{x}" y="250" font-family="{SANS}" font-size="14.5" '
        f'fill="{t["faint"]}">{esc(DETAIL)}</text>'
    )

    # Status pill. Width is estimated from the string; the copy is fixed.
    pill_w = 46 + len(STATUS) * 6.55
    parts.append(
        f'<g transform="translate({x} 272)">'
        f'<rect width="{pill_w:.0f}" height="38" rx="19" fill="{t["raise"]}" '
        f'stroke="{t["hairline"]}" stroke-opacity="{t["ring_op"]}"/>'
        f'<circle cx="21" cy="19" r="4.5" fill="{t["mint"]}">'
        f'<animate attributeName="opacity" values="1;0.28;1" dur="2.6s" '
        f'repeatCount="indefinite"/></circle>'
        f'<text x="36" y="24" font-family="{SANS}" font-size="13.5" '
        f'fill="{muted}">{esc(STATUS)}</text>'
        f"</g>"
    )

    # Outer bezel last, so nothing paints over it.
    parts.append(
        f'<rect x="0.75" y="0.75" width="{W - 1.5}" height="{H - 1.5}" rx="21.25" '
        f'fill="none" stroke="{t["hairline"]}" stroke-opacity="{t["ring_op"]}" '
        f'stroke-width="1.5"/>'
    )
    parts.append("</svg>")
    return "".join(parts)


def main():
    os.makedirs(ASSETS, exist_ok=True)
    for name, t in THEMES.items():
        write(os.path.join(ASSETS, f"banner-{name}.svg"), build(t))


if __name__ == "__main__":
    main()
