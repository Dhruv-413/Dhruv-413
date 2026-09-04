#!/usr/bin/env python3
"""Shared visual language for every SVG this repository generates.

Two palettes, one geometry. `build_banner.py` and `build_readme.py` both
import from here so the hero and the statistics cards cannot drift apart.

Constraints worth remembering before editing:
  * These SVGs are referenced from README.md with <img>, so the browser
    renders them in secure-static mode. No scripts, no external fonts,
    no external images. Everything must be inline.
  * prefers-color-scheme inside the file would follow the *operating
    system*, not the GitHub theme toggle, so we emit one file per theme
    and let <picture> choose. See README.md.
"""

# System stacks only. A webfont would silently fail to load in <img> context.
SANS = (
    "ui-sans-serif, system-ui, -apple-system, 'Segoe UI', "
    "Roboto, 'Helvetica Neue', sans-serif"
)
MONO = (
    "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, "
    "Consolas, 'Liberation Mono', monospace"
)

THEMES = {
    "dark": {
        "name": "dark",
        "bg": "#0A0C13",
        "panel": "#0F121B",
        "raise": "#141826",
        "hairline": "#FFFFFF",
        "hairline_op": "0.07",
        "ring_op": "0.10",
        "text": "#F3F5FA",
        "muted": "#9AA3B7",
        "faint": "#5C6478",
        "accent": "#7C82F9",
        "accent_2": "#A5AAFF",
        "mint": "#3ED6A6",
        "glow_op": "0.30",
        "depth_op": "0.045",
        "grain_op": "0.05",
        # Contribution intensity ramp, empty -> busiest.
        "scale": ["#1A1F2E", "#26306E", "#3D48B4", "#5D67E4", "#949AFF"],
        "track": "#171B29",
        # One ramp for every categorical series, so a language chart and
        # a clock face never disagree about what colour means.
        "series": ["#7C82F9", "#9B8BF7", "#BA90EE", "#4FC7DA", "#3ED6A6", "#69738A"],
    },
    "light": {
        "name": "light",
        # Not pure white: GitHub's light canvas is #ffffff, so a card at
        # #ffffff would have no edge at all.
        "bg": "#F6F7FC",
        "panel": "#FFFFFF",
        "raise": "#FFFFFF",
        "hairline": "#0F1729",
        "hairline_op": "0.10",
        "ring_op": "0.12",
        "text": "#0D1526",
        "muted": "#4E586E",
        "faint": "#7B8496",
        "accent": "#4F46E5",
        "accent_2": "#6366F1",
        "mint": "#0E9F76",
        "glow_op": "0.20",
        "depth_op": "0.65",
        "grain_op": "0.035",
        "scale": ["#EBEEF6", "#C9CDF7", "#9AA0F0", "#6A6FE4", "#4338CA"],
        "track": "#E7EAF3",
        "series": ["#4F46E5", "#6D57DE", "#8B54CC", "#1189A6", "#0E9F76", "#7B8496"],
    },
}

RADIUS = 22          # card corner
PAD = 48             # macro padding, kept generous on purpose


def esc(text):
    """Escape text for XML content."""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def open_svg(width, height, label):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
        f'role="img" aria-label="{esc(label)}">'
    )


def grain_filter(t, fid="grain"):
    """Film grain. Cheap texture that stops flat fills looking synthetic."""
    return (
        f'<filter id="{fid}" x="0" y="0" width="100%" height="100%">'
        f'<feTurbulence type="fractalNoise" baseFrequency="0.85" '
        f'numOctaves="3" stitchTiles="stitch" result="n"/>'
        f'<feColorMatrix type="saturate" values="0" in="n" result="g"/>'
        f'</filter>'
    )


def card(t, width, height, fid="grain"):
    """Double-bezel enclosure: filled shell, grain, then an inset hairline.

    The inner ring is what makes the card read as machined rather than
    as a rectangle with a border.
    """
    return (
        f'<rect width="{width}" height="{height}" rx="{RADIUS}" fill="{t["bg"]}"/>'
        f'<rect width="{width}" height="{height}" rx="{RADIUS}" '
        f'filter="url(#{fid})" opacity="{t["grain_op"]}"/>'
        f'<rect x="0.75" y="0.75" width="{width - 1.5}" height="{height - 1.5}" '
        f'rx="{RADIUS - 0.75}" fill="none" stroke="{t["hairline"]}" '
        f'stroke-opacity="{t["ring_op"]}" stroke-width="1.5"/>'
        f'<rect x="8.5" y="8.5" width="{width - 17}" height="{height - 17}" '
        f'rx="{RADIUS - 8}" fill="none" stroke="{t["hairline"]}" '
        f'stroke-opacity="{t["hairline_op"]}" stroke-width="1"/>'
    )


def eyebrow(t, x, y, text, color=None):
    """Microscopic uppercase tag that precedes every heading."""
    return (
        f'<text x="{x}" y="{y}" font-family="{MONO}" font-size="12" '
        f'font-weight="500" letter-spacing="3.4" '
        f'fill="{color or t["accent"]}">{esc(text.upper())}</text>'
    )


def heading(t, x, y, text, size=34):
    return (
        f'<text x="{x}" y="{y}" font-family="{SANS}" font-size="{size}" '
        f'font-weight="600" letter-spacing="-0.8" '
        f'fill="{t["text"]}">{esc(text)}</text>'
    )


def label(t, x, y, text, size=14, color=None, anchor="start", weight="400"):
    return (
        f'<text x="{x}" y="{y}" font-family="{SANS}" font-size="{size}" '
        f'font-weight="{weight}" text-anchor="{anchor}" '
        f'fill="{color or t["muted"]}">{esc(text)}</text>'
    )


def mono(t, x, y, text, size=13, color=None, anchor="start", spacing="0"):
    return (
        f'<text x="{x}" y="{y}" font-family="{MONO}" font-size="{size}" '
        f'letter-spacing="{spacing}" text-anchor="{anchor}" '
        f'fill="{color or t["faint"]}">{esc(text)}</text>'
    )


def write(path, body):
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(body + "\n")
    print(f"wrote {path}")
