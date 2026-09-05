"""Renders every profile graphic as one cartographic set.

Cards share a survey-map language: neat lines, graticules, hypsometric tints
that lighten with altitude, and monospace legends. One API round trip feeds
all of them, so the whole README stays consistent and self-hosted.
"""

import hashlib
import json
import math
import os
import re
import urllib.error
import urllib.request

USERNAME = os.environ.get("GITHUB_USER", "Dhruv-413")
TOKEN = os.environ["GITHUB_TOKEN"]
OUT_DIR = os.environ.get("OUT_DIR", "assets")

BG = "#0d0f17"
SURFACE = "#161b28"
LINE = "#2f3648"
INK = "#f4f6fb"
MUTED = "#aab2d0"
DIM = "#7f89ad"

CYAN = "#8be9fd"
GREEN = "#50fa7b"
PINK = "#ff79c6"
PURPLE = "#bd93f9"

# Hypsometric ramp: lowlands dark, summits light (Patterson & Jenny convention).
RAMP = [
    (0.00, (30, 36, 56)),
    (0.30, (61, 63, 107)),
    (0.55, (125, 91, 176)),
    (0.75, (189, 147, 249)),
    (0.90, (255, 121, 198)),
    (1.00, (255, 184, 230)),
]

SANS = "Segoe UI, Helvetica Neue, Helvetica, Arial, sans-serif"
MONO = "SFMono-Regular, Consolas, Liberation Mono, Menlo, monospace"

DEVICON = "https://cdn.jsdelivr.net/gh/devicons/devicon/icons/{}.svg"
ICON_LIMIT = 30_000

# GitHub language name -> devicon slug.
LANG_ICON = {
    "Python": "python/python-original",
    "JavaScript": "javascript/javascript-original",
    "TypeScript": "typescript/typescript-original",
    "Jupyter Notebook": "jupyter/jupyter-original",
    "HTML": "html5/html5-original",
    "CSS": "css3/css3-original",
    "SCSS": "sass/sass-original",
    "Java": "java/java-original",
    "Go": "go/go-original",
    "C++": "cplusplus/cplusplus-original",
    "C": "c/c-original",
    "C#": "csharp/csharp-original",
    "Shell": "bash/bash-original",
    "Dockerfile": "docker/docker-original",
    "Dart": "dart/dart-original",
    "Kotlin": "kotlin/kotlin-original",
    "PHP": "php/php-original",
    "Ruby": "ruby/ruby-original",
    "Swift": "swift/swift-original",
    "Rust": "rust/rust-original",
    "Vue": "vuejs/vuejs-original",
    "PowerShell": "powershell/powershell-original",
}

STACK = [
    (
        "LANGUAGES &#38; ML",
        [
            ("Python", "python/python-original", "#3776AB"),
            ("TypeScript", "typescript/typescript-original", "#3178C6"),
            ("JavaScript", "javascript/javascript-original", "#F7DF1E"),
            ("Go", "go/go-original", "#00ADD8"),
            ("PyTorch", "pytorch/pytorch-original", "#EE4C2C"),
            ("TensorFlow", "tensorflow/tensorflow-original", "#FF6F00"),
            ("Pandas", "pandas/pandas-original", "#150458"),
            ("NumPy", "numpy/numpy-original", "#013243"),
            ("Jupyter", "jupyter/jupyter-original", "#F37626"),
        ],
    ),
    (
        "WEB &#38; DATA",
        [
            ("React", "react/react-original", "#61DAFB"),
            ("FastAPI", "fastapi/fastapi-original", "#009688"),
            ("Tailwind", "tailwindcss/tailwindcss-original", "#06B6D4"),
            ("PostgreSQL", "postgresql/postgresql-original", "#4169E1"),
            ("MySQL", "mysql/mysql-original", "#4479A1"),
            ("Redis", "redis/redis-original", "#DC382D"),
            ("Firebase", "firebase/firebase-plain", "#FFCA28"),
            ("Supabase", "supabase/supabase-original", "#3ECF8E"),
        ],
    ),
    (
        "TOOLS &#38; CLOUD",
        [
            ("Docker", "docker/docker-original", "#2496ED"),
            ("Git", "git/git-original", "#F05032"),
            ("Azure", "azure/azure-original", "#0078D4"),
            ("Linux", "linux/linux-plain", "#FCC624"),
            ("GitLab", "gitlab/gitlab-original", "#FC6D26"),
            ("npm", "npm/npm-original-wordmark", "#CB3837"),
        ],
    ),
]

QUERY = """
query($login: String!) {
  user(login: $login) {
    followers { totalCount }
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false,
                 orderBy: {field: STARGAZERS, direction: DESC}) {
      totalCount
      nodes {
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
  }
}
"""

_icon_cache = {}


def fetch():
    body = json.dumps({"query": QUERY, "variables": {"login": USERNAME}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={
            "Authorization": f"bearer {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": USERNAME,
        },
    )
    with urllib.request.urlopen(req, timeout=45) as resp:
        payload = json.load(resp)
    if "errors" in payload:
        raise SystemExit(f"GraphQL error: {payload['errors']}")
    return payload["data"]["user"]


def icon(slug, x, y, size):
    """Inline a devicon as a nested <svg>; external refs never load inside <img>."""
    if slug not in _icon_cache:
        try:
            with urllib.request.urlopen(DEVICON.format(slug), timeout=20) as resp:
                raw = resp.read().decode("utf-8", "replace")
            if len(raw) > ICON_LIMIT:
                raw = None
        except (urllib.error.URLError, TimeoutError, OSError):
            raw = None
        if raw:
            raw = re.sub(r"<\?xml.*?\?>", "", raw, flags=re.S)
            raw = re.sub(r"<!--.*?-->", "", raw, flags=re.S)
            m = re.search(r'viewBox="([^"]+)"', raw)
            view = m.group(1) if m else "0 0 128 128"
            inner = re.sub(r"^.*?<svg[^>]*>", "", raw, flags=re.S)
            inner = re.sub(r"</svg>\s*$", "", inner, flags=re.S)
            _icon_cache[slug] = (view, inner.strip())
        else:
            _icon_cache[slug] = None

    entry = _icon_cache.get(slug)
    if not entry:
        return ""
    view, inner = entry
    return (
        f'<svg x="{x:.1f}" y="{y:.1f}" width="{size}" height="{size}" '
        f'viewBox="{view}" overflow="visible">{inner}</svg>'
    )


def plate(x, y, size, radius=6):
    return (
        f'<rect x="{x - 4:.1f}" y="{y - 4:.1f}" width="{size + 8}" height="{size + 8}" '
        f'rx="{radius}" fill="#ffffff" fill-opacity="0.06" />'
    )


def tint(t):
    t = min(max(t, 0.0), 1.0)
    for i in range(len(RAMP) - 1):
        p0, c0 = RAMP[i]
        p1, c1 = RAMP[i + 1]
        if t <= p1:
            u = (t - p0) / (p1 - p0) if p1 > p0 else 0.0
            return "#%02x%02x%02x" % tuple(
                round(c0[k] + (c1[k] - c0[k]) * u) for k in range(3)
            )
    return "#%02x%02x%02x" % RAMP[-1][1]


def for_dark(hex_color):
    """Lift very dark brand colours so they stay visible on the panel."""
    h = (hex_color or "#8b93b0").lstrip("#")
    if len(h) != 6:
        h = "8b93b0"
    r, g, b = (int(h[i : i + 2], 16) for i in (0, 2, 4))
    lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    if lum >= 0.34:
        return f"#{h}"
    k = (0.34 - lum) / 0.34 * 0.72
    return "#%02x%02x%02x" % (
        round(r + (255 - r) * k),
        round(g + (255 - g) * k),
        round(b + (255 - b) * k),
    )


def jitter(index, salt):
    digest = hashlib.sha256(f"{USERNAME}:{salt}:{index}".encode()).digest()
    return int.from_bytes(digest[:4], "big") / 0xFFFFFFFF


def defs(extra=""):
    return f'''<defs>
    <filter id="grain" x="0" y="0" width="100%" height="100%">
      <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="3" />
      <feColorMatrix type="saturate" values="0" />
    </filter>
    <pattern id="hatch" width="6" height="6" patternTransform="rotate(45)"
             patternUnits="userSpaceOnUse">
      <line x1="0" y1="0" x2="0" y2="6" stroke="#ffffff" stroke-width="1" stroke-opacity="0.10" />
    </pattern>
    <style>
      /* Nothing that carries information may depend on an animation running.
         An image-embedded SVG restarts its timeline whenever the host page
         re-rasterises, so opacity is never animated on text -- only
         transform. Worst case a label is a few pixels off, never invisible. */
      @keyframes draw {{ from {{ stroke-dashoffset: 1; }} to {{ stroke-dashoffset: 0; }} }}
      @keyframes rise {{ from {{ transform: translateY(9px); }} to {{ transform: translateY(0); }} }}
      @keyframes glow {{ 0%, 100% {{ opacity: 0.4; }} 50% {{ opacity: 1; }} }}
      @keyframes wipe {{ from {{ transform: scaleX(0); }} to {{ transform: scaleX(1); }} }}
      .ln path {{ stroke-dasharray: 1; animation: draw 2.2s ease-out backwards; }}
      .pk {{ animation: glow 3.4s ease-in-out infinite; }}
      .tx {{ animation: rise 0.7s cubic-bezier(.2,.7,.3,1) backwards; }}
      .bar {{ transform-origin: left center; animation: wipe 1s cubic-bezier(.2,.7,.3,1) backwards; }}
      @media (prefers-reduced-motion: reduce) {{
        .ln path, .pk, .tx, .bar {{ animation: none; }}
      }}
    </style>
    {extra}
  </defs>'''


def frame(w, h, title, right=""):
    """Neat line, title block and source note shared by every panel."""
    note = (
        f'<text x="{w - 22}" y="30" fill="{MUTED}" font-size="11.5" font-family="{MONO}" '
        f'text-anchor="end">{right}</text>'
        if right
        else ""
    )
    return f'''<rect width="{w}" height="{h}" rx="14" fill="{SURFACE}" />
  <rect width="{w}" height="{h}" filter="url(#grain)" opacity="0.05" />
  <text x="22" y="30" fill="{INK}" font-size="12" font-family="{MONO}"
        letter-spacing="2.4" opacity="0.92">{title}</text>{note}
  <line x1="22" y1="44" x2="{w - 22}" y2="44" stroke="{LINE}" stroke-width="1" />'''


def outline(w, h):
    return (
        f'<rect x="0.75" y="0.75" width="{w - 1.5}" height="{h - 1.5}" rx="14" '
        f'fill="none" stroke="{LINE}" stroke-width="1.5" />'
    )


def doc(w, h, label, body, extra_defs=""):
    return (
        f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
        f'xmlns="http://www.w3.org/2000/svg" '
        f'xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'role="img" aria-label="{label}">'
        f"{defs(extra_defs)}{body}</svg>\n"
    )


def weekly(user):
    cal = user["contributionsCollection"]["contributionCalendar"]
    weeks = [sum(d["contributionCount"] for d in w["contributionDays"]) for w in cal["weeks"]]
    starts = [w["contributionDays"][0]["date"] for w in cal["weeks"]]
    return weeks, starts, cal["totalContributions"]


def daily(user):
    cal = user["contributionsCollection"]["contributionCalendar"]
    return [
        (d["date"], d["contributionCount"])
        for w in cal["weeks"]
        for d in w["contributionDays"]
    ]


def streaks(days):
    longest = run = 0
    for _, count in days:
        run = run + 1 if count > 0 else 0
        longest = max(longest, run)
    current = 0
    for i in range(len(days) - 1, -1, -1):
        if days[i][1] > 0:
            current += 1
        elif i == len(days) - 1:
            continue
        else:
            break
    return current, longest


# --------------------------------------------------------------------------- #
# Terrain field shared by the header and footer
# --------------------------------------------------------------------------- #

COLS, ROWS = 176, 50
LEVELS = 15


def smoothstep(t):
    return t * t * (3 - 2 * t)


def value_noise(cols, rows, gw, gh, salt):
    grid = [[jitter(gy * gw + gx, salt) for gx in range(gw)] for gy in range(gh)]
    field = []
    for r in range(rows):
        v = r / (rows - 1) * (gh - 1)
        y0 = min(int(v), gh - 2)
        ty = smoothstep(v - y0)
        row = []
        for c in range(cols):
            u = c / (cols - 1) * (gw - 1)
            x0 = min(int(u), gw - 2)
            tx = smoothstep(u - x0)
            top = grid[y0][x0] * (1 - tx) + grid[y0][x0 + 1] * tx
            bot = grid[y0 + 1][x0] * (1 - tx) + grid[y0 + 1][x0 + 1] * tx
            row.append(top * (1 - ty) + bot * ty)
        field.append(row)
    return field


def build_field(weeks):
    peak = max(weeks) or 1
    noise = value_noise(COLS, ROWS, 7, 4, "base")
    fine = value_noise(COLS, ROWS, 13, 7, "detail")
    field = [[0.0] * COLS for _ in range(ROWS)]
    span = max(len(weeks) - 1, 1)

    for i, count in enumerate(weeks):
        if count <= 0:
            continue
        amp = 0.36 + 0.64 * (count / peak) ** 0.45
        cx = i / span * (COLS - 1)
        cy = ROWS * (0.24 + 0.52 * jitter(i, "y"))
        sx = 6.0 + 5.0 * amp
        sy = 4.2 + 4.0 * amp
        for r in range(max(0, int(cy - 4 * sy)), min(ROWS, int(cy + 4 * sy) + 1)):
            dy = (r - cy) / sy
            for c in range(max(0, int(cx - 4 * sx)), min(COLS, int(cx + 4 * sx) + 1)):
                dx = (c - cx) / sx
                field[r][c] += amp * math.exp(-0.5 * (dx * dx + dy * dy))

    for r in range(ROWS):
        edge = math.sin(math.pi * min(max(r / (ROWS - 1), 0.0), 1.0)) ** 0.55
        for c in range(COLS):
            field[r][c] += 0.62 * noise[r][c] + 0.24 * fine[r][c]
            field[r][c] *= edge

    lo = min(min(row) for row in field)
    hi = max(max(row) for row in field)
    rng = (hi - lo) or 1.0
    return [[(v - lo) / rng for v in row] for row in field]


def marching_squares(field, level):
    segs = []
    for r in range(ROWS - 1):
        for c in range(COLS - 1):
            a, b = field[r][c], field[r][c + 1]
            d, e = field[r + 1][c], field[r + 1][c + 1]
            idx = (a > level) + 2 * (b > level) + 4 * (e > level) + 8 * (d > level)
            if idx in (0, 15):
                continue
            top = (c + (level - a) / (b - a), r) if b != a else (c, r)
            right = (c + 1, r + (level - b) / (e - b)) if e != b else (c + 1, r)
            bottom = (c + (level - d) / (e - d), r + 1) if e != d else (c, r + 1)
            left = (c, r + (level - a) / (d - a)) if d != a else (c, r)
            if idx in (1, 14):
                segs.append((left, top))
            elif idx in (2, 13):
                segs.append((top, right))
            elif idx in (3, 12):
                segs.append((left, right))
            elif idx in (4, 11):
                segs.append((right, bottom))
            elif idx in (6, 9):
                segs.append((top, bottom))
            elif idx in (7, 8):
                segs.append((left, bottom))
            elif idx == 5:
                segs.append((left, top))
                segs.append((right, bottom))
            elif idx == 10:
                segs.append((top, right))
                segs.append((left, bottom))
    return segs


def chain(segs):
    def key(p):
        return (round(p[0], 3), round(p[1], 3))

    adj = {}
    for i, (p, q) in enumerate(segs):
        adj.setdefault(key(p), []).append(i)
        adj.setdefault(key(q), []).append(i)

    used = [False] * len(segs)
    paths = []
    for i in range(len(segs)):
        if used[i]:
            continue
        used[i] = True
        pts = [segs[i][0], segs[i][1]]
        for direction in (0, 1):
            while True:
                anchor = key(pts[-1] if direction == 0 else pts[0])
                nxt = next((j for j in adj.get(anchor, []) if not used[j]), None)
                if nxt is None:
                    break
                used[nxt] = True
                a, b = segs[nxt]
                far = b if key(a) == anchor else a
                pts.append(far) if direction == 0 else pts.insert(0, far)
        if len(pts) >= 5:
            paths.append(pts)
    return paths


def chaikin(pts, iterations=2):
    closed = abs(pts[0][0] - pts[-1][0]) < 1e-6 and abs(pts[0][1] - pts[-1][1]) < 1e-6
    for _ in range(iterations):
        out = [] if closed else [pts[0]]
        for i in range(len(pts) - 1):
            (x0, y0), (x1, y1) = pts[i], pts[i + 1]
            out.append((x0 * 0.75 + x1 * 0.25, y0 * 0.75 + y1 * 0.25))
            out.append((x0 * 0.25 + x1 * 0.75, y0 * 0.25 + y1 * 0.75))
        out.append(out[0] if closed else pts[-1])
        pts = out
    return pts


def contour_layers(field, w, h, flip=False, opacity=1.0):
    sx, sy = w / (COLS - 1), h / (ROWS - 1)
    layers = []
    for li in range(1, LEVELS):
        paths = chain(marching_squares(field, li / LEVELS))
        if not paths:
            continue
        t = li / (LEVELS - 1)
        body = ""
        for p in paths:
            pts = chaikin(p)
            coords = [
                (x * sx, (h - y * sy) if flip else y * sy) for x, y in pts
            ]
            d = f"M{coords[0][0]:.1f} {coords[0][1]:.1f}" + "".join(
                f"L{x:.1f} {y:.1f}" for x, y in coords[1:]
            )
            body += f'<path d="{d}" pathLength="1" style="animation-delay:{0.15 + t * 0.9:.2f}s" />'
        layers.append(
            f'<g class="ln" fill="none" stroke="{tint(t)}" stroke-width="{0.9 + 0.9 * t:.2f}" '
            f'stroke-opacity="{(0.42 + 0.52 * t) * opacity:.2f}" stroke-linecap="round" '
            f'stroke-linejoin="round">{body}</g>'
        )
    return "".join(layers)


# --------------------------------------------------------------------------- #
# Cards
# --------------------------------------------------------------------------- #

HEAD_W, HEAD_H = 1200, 340

CREDENTIALS = ["B.TECH CSE", "EX&#8209;ONGC", "SAP HACKFEST TOP 50"]


def chips(items, x, y, size=10.5):
    """Small outlined pills; width estimated from monospace advance."""
    out = ""
    cx = x
    for label in items:
        chars = len(re.sub(r"&#\d+;", "_", label))
        w = chars * size * 0.62 + 22
        out += (
            f'<rect x="{cx:.1f}" y="{y:.1f}" width="{w:.1f}" height="23" rx="11.5" '
            f'fill="#ffffff" fill-opacity="0.07" stroke="{MUTED}" stroke-opacity="0.35" '
            f'stroke-width="1" />'
            f'<text x="{cx + w / 2:.1f}" y="{y + 15.5:.1f}" fill="{MUTED}" font-size="{size}" '
            f'font-family="{MONO}" letter-spacing="0.8" text-anchor="middle">{label}</text>'
        )
        cx += w + 9
    return out


def render_header(user, field):
    weeks, _, total = weekly(user)
    peak = max(weeks) or 1
    span = max(len(weeks) - 1, 1)

    dots = ""
    for n, i in enumerate(sorted(range(len(weeks)), key=lambda k: weeks[k], reverse=True)[:6]):
        if weeks[i] <= 0:
            continue
        x = i / span * HEAD_W
        y = (0.24 + 0.52 * jitter(i, "y")) * HEAD_H
        r = 2.0 + 1.6 * (0.55 + 0.45 * weeks[i] / peak)
        dots += (
            f'<circle class="pk" cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{CYAN}" '
            f'style="animation-delay:{0.9 + 0.12 * n:.2f}s" />'
        )

    grads = f'''<radialGradient id="g1" cx="18%" cy="26%" r="62%">
      <stop offset="0%" stop-color="{PURPLE}" stop-opacity="0.30" />
      <stop offset="100%" stop-color="{PURPLE}" stop-opacity="0" />
    </radialGradient>
    <radialGradient id="g2" cx="76%" cy="72%" r="60%">
      <stop offset="0%" stop-color="{PINK}" stop-opacity="0.26" />
      <stop offset="100%" stop-color="{PINK}" stop-opacity="0" />
    </radialGradient>
    <linearGradient id="scrim" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="{BG}" stop-opacity="0.82" />
      <stop offset="40%" stop-color="{BG}" stop-opacity="0.46" />
      <stop offset="72%" stop-color="{BG}" stop-opacity="0" />
    </linearGradient>
    <radialGradient id="halo" cx="23%" cy="52%" r="44%">
      <stop offset="0%" stop-color="{BG}" stop-opacity="0.88" />
      <stop offset="58%" stop-color="{BG}" stop-opacity="0.55" />
      <stop offset="100%" stop-color="{BG}" stop-opacity="0" />
    </radialGradient>
    <clipPath id="frameClip"><rect width="{HEAD_W}" height="{HEAD_H}" rx="16" /></clipPath>'''

    body = f'''<g clip-path="url(#frameClip)">
    <rect width="{HEAD_W}" height="{HEAD_H}" fill="{BG}" />
    <rect width="{HEAD_W}" height="{HEAD_H}" fill="url(#g1)" />
    <rect width="{HEAD_W}" height="{HEAD_H}" fill="url(#g2)" />
    {contour_layers(field, HEAD_W, HEAD_H)}{dots}
    <rect width="{HEAD_W}" height="{HEAD_H}" fill="url(#scrim)" />
    <rect width="{HEAD_W}" height="{HEAD_H}" fill="url(#halo)" />
    <rect width="{HEAD_W}" height="{HEAD_H}" filter="url(#grain)" opacity="0.05" />
    <g class="tx" style="animation-delay:0.15s">
      <text x="64" y="118" fill="{INK}" font-size="54" font-weight="700" letter-spacing="2"
            font-family="{SANS}">Dhruv Gupta</text>
    </g>
    <g class="tx" style="animation-delay:0.30s">
      <circle cx="72" cy="152" r="4.5" fill="{GREEN}" class="pk" style="animation-delay:0.9s" />
      <text x="88" y="158" fill="{PINK}" font-size="19" font-weight="600" letter-spacing="1.2"
            font-family="{SANS}">Software Engineer at Deloitte</text>
    </g>
    <g class="tx" style="animation-delay:0.45s">
      <text x="66" y="194" fill="{INK}" font-size="14.5" font-family="{MONO}" opacity="0.90">machine learning &#183; full&#8209;stack &#183; distributed systems</text>
    </g>
    <g class="tx" style="animation-delay:0.60s">{chips(CREDENTIALS, 65, 212)}</g>
    <g class="tx" style="animation-delay:0.75s">
      <text x="66" y="270" fill="{MUTED}" font-size="12.5" font-family="{MONO}">terrain mapped from {total:,} contributions this year</text>
    </g>
  </g>
  <rect x="0.75" y="0.75" width="{HEAD_W - 1.5}" height="{HEAD_H - 1.5}" rx="16" fill="none"
        stroke="#3b3d54" stroke-width="1.5" />'''
    return doc(HEAD_W, HEAD_H, f"{USERNAME} contribution terrain", body, grads)


FOOT_W, FOOT_H = 1200, 150


def render_footer(field):
    grads = f'''<linearGradient id="fscrim" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="{BG}" stop-opacity="0.92" />
      <stop offset="62%" stop-color="{BG}" stop-opacity="0.78" />
      <stop offset="88%" stop-color="{BG}" stop-opacity="0.34" />
      <stop offset="100%" stop-color="{BG}" stop-opacity="0" />
    </linearGradient>
    <clipPath id="footClip"><rect width="{FOOT_W}" height="{FOOT_H}" rx="16" /></clipPath>'''

    body = f'''<g clip-path="url(#footClip)">
    <rect width="{FOOT_W}" height="{FOOT_H}" fill="{BG}" />
    <g opacity="0.85">{contour_layers(field, FOOT_W, FOOT_H * 2.2, flip=True, opacity=0.75)}</g>
    <rect width="{FOOT_W}" height="{FOOT_H}" fill="url(#fscrim)" />
    <rect width="{FOOT_W}" height="{FOOT_H}" filter="url(#grain)" opacity="0.05" />
    <g class="tx" style="animation-delay:0.2s">
      <text x="{FOOT_W / 2}" y="62" fill="{INK}" font-size="20" font-weight="600"
            text-anchor="middle" font-family="{SANS}">Always mapping new ground.</text>
      <text x="{FOOT_W / 2}" y="90" fill="{MUTED}" font-size="13.5" text-anchor="middle"
            font-family="{SANS}">Open to conversations about ML systems, backend architecture, and hard problems.</text>
      <text x="{FOOT_W / 2}" y="118" fill="{MUTED}" font-size="11.5" text-anchor="middle"
            font-family="{MONO}">dhruvgupta6580@gmail.com &#183; Ghaziabad, India</text>
    </g>
  </g>
  <rect x="0.75" y="0.75" width="{FOOT_W - 1.5}" height="{FOOT_H - 1.5}" rx="16" fill="none"
        stroke="#3b3d54" stroke-width="1.5" />'''
    return doc(FOOT_W, FOOT_H, "footer", body, grads)


PROF_W, PROF_H = 1200, 300


def render_activity(user):
    weeks, starts, total = weekly(user)
    pad_l, pad_r, pad_t, pad_b = 26, 26, 88, 54
    plot_w = PROF_W - pad_l - pad_r
    plot_h = PROF_H - pad_t - pad_b
    base_y = pad_t + plot_h
    peak = max(weeks) or 1
    span = max(len(weeks) - 1, 1)

    pts = [
        (pad_l + i / span * plot_w, base_y - (c / peak) * plot_h)
        for i, c in enumerate(weeks)
    ]
    d = f"M{pts[0][0]:.1f} {pts[0][1]:.1f}"
    for i in range(len(pts) - 1):
        x0, y0 = pts[i]
        x1, y1 = pts[i + 1]
        mx = (x0 + x1) / 2
        d += f"C{mx:.1f} {y0:.1f},{mx:.1f} {y1:.1f},{x1:.1f} {y1:.1f}"
    area = d + f"L{pts[-1][0]:.1f} {base_y:.1f}L{pts[0][0]:.1f} {base_y:.1f}Z"

    steps = 9
    bands = "".join(
        f'<rect x="{pad_l}" y="{base_y - plot_h * (i + 1) / steps:.1f}" width="{plot_w}" '
        f'height="{plot_h / steps + 1:.1f}" fill="{tint(i / (steps - 1))}" fill-opacity="0.92" />'
        for i in range(steps)
    )
    grid = "".join(
        f'<line x1="{pad_l}" y1="{base_y - plot_h * f:.1f}" x2="{PROF_W - pad_r}" '
        f'y2="{base_y - plot_h * f:.1f}" stroke="{LINE}" stroke-width="1" stroke-dasharray="3 5" />'
        for f in (0.25, 0.5, 0.75, 1.0)
    )

    ticks = ""
    seen, last_x = set(), -999.0
    for i, s in enumerate(starts):
        m = s[:7]
        if m in seen:
            continue
        seen.add(m)
        x = pad_l + i / span * plot_w
        if x - last_x < 46:
            continue
        last_x = x
        month = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"][int(s[5:7]) - 1]
        ticks += (
            f'<line x1="{x:.1f}" y1="{base_y}" x2="{x:.1f}" y2="{base_y + 6}" '
            f'stroke="{DIM}" stroke-width="1" />'
            f'<text x="{x:.1f}" y="{base_y + 22}" fill="{DIM}" font-size="10.5" '
            f'font-family="{MONO}" text-anchor="middle">{month}</text>'
        )

    hi = weeks.index(peak)
    hx = pad_l + hi / span * plot_w
    hy = base_y - plot_h
    anchor = "end" if hx > PROF_W - 120 else "middle"
    callout = (
        f'<line x1="{hx:.1f}" y1="{hy:.1f}" x2="{hx:.1f}" y2="{hy - 12:.1f}" '
        f'stroke="{CYAN}" stroke-width="1" stroke-opacity="0.7" />'
        f'<circle class="pk" cx="{hx:.1f}" cy="{hy:.1f}" r="3.5" fill="{CYAN}" />'
        f'<text x="{hx - 10 if anchor == "end" else hx:.1f}" y="{hy - 18:.1f}" fill="{CYAN}" '
        f'font-size="11" font-family="{MONO}" text-anchor="{anchor}">peak {peak}</text>'
    )
    scale = "".join(
        f'<rect x="{pad_l + i * 22}" y="{PROF_H - 22}" width="22" height="5" fill="{tint(i / 7)}" />'
        for i in range(8)
    )

    body = f'''{frame(PROF_W, PROF_H, "ELEVATION PROFILE &#183; 52 WEEKS", f"{total:,} contributions")}
  {grid}
  <clipPath id="terrain"><path d="{area}" /></clipPath>
  <g clip-path="url(#terrain)">{bands}
    <rect x="{pad_l}" y="{pad_t}" width="{plot_w}" height="{plot_h}" fill="url(#hatch)" />
  </g>
  <path d="{d}" fill="none" stroke="{INK}" stroke-width="1.6" stroke-opacity="0.85"
        stroke-linejoin="round" stroke-linecap="round" />
  <line x1="{pad_l}" y1="{base_y}" x2="{PROF_W - pad_r}" y2="{base_y}" stroke="{DIM}" stroke-width="1.2" />
  {ticks}{callout}{scale}
  <text x="{pad_l + 8 * 22 + 10}" y="{PROF_H - 17}" fill="{DIM}" font-size="10.5"
        font-family="{MONO}">low &#8594; high weekly volume</text>
  {outline(PROF_W, PROF_H)}'''
    return doc(PROF_W, PROF_H, "weekly contribution elevation profile", body)


LANG_W, LANG_H = 592, 300


def _worst(row, side):
    total = sum(row)
    if total <= 0 or side <= 0:
        return float("inf")
    return max(
        (side * side * max(row)) / (total * total),
        (total * total) / (side * side * min(row)),
    )


def squarify(values, x, y, w, h):
    """Squarified treemap: areas must already sum to w*h, sorted descending."""
    rects = []
    vals = list(values)
    while vals:
        row, rest = [vals[0]], vals[1:]
        while rest:
            side = min(w, h)
            if _worst(row + [rest[0]], side) <= _worst(row, side):
                row.append(rest.pop(0))
            else:
                break
        total = sum(row)
        if w >= h:
            rw = total / h if h else 0
            ry = y
            for v in row:
                rh = v / rw if rw else 0
                rects.append((x, ry, rw, rh))
                ry += rh
            x, w = x + rw, w - rw
        else:
            rh = total / w if w else 0
            rx = x
            for v in row:
                rw2 = v / rh if rh else 0
                rects.append((rx, y, rw2, rh))
                rx += rw2
            y, h = y + rh, h - rh
        vals = rest
    return rects


def readable_on(hex_color):
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i : i + 2], 16) for i in (0, 2, 4))
    return "#0d1119" if (0.299 * r + 0.587 * g + 0.114 * b) / 255 > 0.62 else "#ffffff"


def render_languages(user):
    # Count repositories per language: byte counts let notebooks swamp everything.
    totals, colors = {}, {}
    for repo in user["repositories"]["nodes"]:
        for edge in repo["languages"]["edges"]:
            name = edge["node"]["name"]
            totals[name] = totals.get(name, 0) + 1
            colors[name] = edge["node"]["color"]

    ranked = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)[:7]
    grand = sum(v for _, v in ranked) or 1

    px, py = 26, 62
    pw, ph = LANG_W - 52, LANG_H - 62 - 26
    area = pw * ph
    rects = squarify([v / grand * area for _, v in ranked], px, py, pw, ph)

    tiles = ""
    for i, ((name, count), (rx, ry, rw, rh)) in enumerate(zip(ranked, rects)):
        col = for_dark(colors.get(name))
        gap = 2.0
        bx, by = rx + gap, ry + gap
        bw, bh = max(rw - gap * 2, 1), max(rh - gap * 2, 1)
        fg = readable_on(col)
        share = count / grand * 100

        inner = ""
        if bw >= 92 and bh >= 62:
            glyph = icon(LANG_ICON.get(name, ""), bx + 12, by + 12, 22)
            inner = (
                f"{glyph}"
                f'<text x="{bx + 12:.1f}" y="{by + 56:.1f}" fill="{fg}" font-size="13.5" '
                f'font-weight="600" font-family="{SANS}">{name}</text>'
                f'<text x="{bx + 12:.1f}" y="{by + 75:.1f}" fill="{fg}" fill-opacity="0.78" '
                f'font-size="11.5" font-family="{MONO}">{count} repos &#183; {share:.0f}%</text>'
            )
        elif bw >= 60 and bh >= 46:
            glyph = icon(LANG_ICON.get(name, ""), bx + 10, by + 10, 18)
            inner = (
                f"{glyph}"
                f'<text x="{bx + 10:.1f}" y="{by + 46:.1f}" fill="{fg}" font-size="11.5" '
                f'font-weight="600" font-family="{SANS}">{name}</text>'
            )
        elif bw >= 30 and bh >= 30:
            inner = icon(LANG_ICON.get(name, ""), bx + bw / 2 - 9, by + bh / 2 - 9, 18)

        tiles += (
            f'<g class="tx" style="animation-delay:{0.07 * i:.2f}s">'
            f'<rect x="{bx:.1f}" y="{by:.1f}" width="{bw:.1f}" height="{bh:.1f}" rx="7" '
            f'fill="{col}" fill-opacity="0.92" />'
            f'<rect x="{bx:.1f}" y="{by:.1f}" width="{bw:.1f}" height="{bh:.1f}" rx="7" '
            f'fill="url(#hatch)" />'
            f'<rect x="{bx:.1f}" y="{by:.1f}" width="{bw:.1f}" height="{bh:.1f}" rx="7" '
            f'fill="none" stroke="#ffffff" stroke-opacity="0.14" stroke-width="1" />'
            f"{inner}</g>"
        )

    body = f'''{frame(LANG_W, LANG_H, "LAND COVER &#183; LANGUAGES", f"{user['repositories']['totalCount']} repos")}
  {tiles}
  {outline(LANG_W, LANG_H)}'''
    return doc(LANG_W, LANG_H, "language land cover", body)


STAT_W, STAT_H = 592, 300


def render_stats(user):
    days = daily(user)
    current, longest = streaks(days)
    contrib = user["contributionsCollection"]
    stars = sum(r["stargazerCount"] for r in user["repositories"]["nodes"])

    commits = contrib["totalCommitContributions"]
    prs = contrib["totalPullRequestContributions"]
    issues = contrib["totalIssueContributions"]
    mix = [("Commits", commits, PINK), ("Pull requests", prs, PURPLE), ("Issues", issues, CYAN)]
    total = max(commits + prs + issues, 1)

    cx, cy, r = 132, 178, 62
    circ = 2 * math.pi * r
    arcs = ""
    acc = 0.0
    for i, (_, value, color) in enumerate(mix):
        frac = value / total
        if frac <= 0:
            continue
        arcs += (
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{color}" '
            f'stroke-width="19" pathLength="1" '
            f'stroke-dasharray="{frac:.5f} {1 - frac:.5f}" '
            f'stroke-dashoffset="{-acc:.5f}" '
            f'transform="rotate(-90 {cx} {cy})" />'
        )
        acc += frac

    donut = (
        f'<g class="tx" style="animation-delay:0.15s">'
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#ffffff" '
        f'stroke-opacity="0.06" stroke-width="19" />{arcs}'
        f'</g>'
        f'<g class="tx" style="animation-delay:0.35s">'
        f'<text x="{cx}" y="{cy - 2}" fill="{INK}" font-size="27" font-weight="700" '
        f'text-anchor="middle" font-family="{SANS}">{total:,}</text>'
        f'<text x="{cx}" y="{cy + 17}" fill="{DIM}" font-size="10" text-anchor="middle" '
        f'font-family="{MONO}" letter-spacing="1.2">CONTRIBUTIONS</text></g>'
    )

    legend = ""
    ly = 80
    for i, (label, value, color) in enumerate(mix):
        legend += (
            f'<g class="tx" style="animation-delay:{0.08 * i:.2f}s">'
            f'<rect x="238" y="{ly - 9}" width="10" height="10" rx="3" fill="{color}" />'
            f'<text x="256" y="{ly}" fill="{MUTED}" font-size="12.5" font-family="{SANS}">{label}</text>'
            f'<text x="{STAT_W - 26}" y="{ly}" fill="{INK}" font-size="13" font-weight="600" '
            f'font-family="{MONO}" text-anchor="end">{value:,}</text></g>'
        )
        ly += 26

    figures = [
        ("CURRENT STREAK", f"{current}d", GREEN),
        ("LONGEST STREAK", f"{longest}d", PINK),
        ("STARS EARNED", f"{stars:,}", PURPLE),
        ("FOLLOWERS", f"{user['followers']['totalCount']}", CYAN),
    ]
    tiles = f'<line x1="238" y1="168" x2="{STAT_W - 26}" y2="168" stroke="{LINE}" stroke-width="1" />'
    for i, (label, value, color) in enumerate(figures):
        tx = 238 + (i % 2) * 168
        ty = 200 + (i // 2) * 54
        tiles += (
            f'<g class="tx" style="animation-delay:{0.3 + 0.06 * i:.2f}s">'
            f'<line x1="{tx}" y1="{ty - 14}" x2="{tx}" y2="{ty + 8}" stroke="{color}" stroke-width="2" />'
            f'<text x="{tx + 11}" y="{ty}" fill="{INK}" font-size="20" font-weight="700" '
            f'font-family="{SANS}">{value}</text>'
            f'<text x="{tx + 11}" y="{ty + 18}" fill="{DIM}" font-size="9.5" '
            f'font-family="{MONO}" letter-spacing="1.1">{label}</text></g>'
        )

    body = f'''{frame(STAT_W, STAT_H, "CONTRIBUTION MIX &#183; 12 MONTHS", "@" + USERNAME)}
  {donut}{legend}{tiles}
  {outline(STAT_W, STAT_H)}'''
    return doc(STAT_W, STAT_H, "contribution mix", body)


STACK_W = 1200


def render_stack():
    col_w = (STACK_W - 52) / 3
    row_h = 30
    tallest = max(len(items) for _, items in STACK)
    height = 74 + tallest * row_h + 22

    out = ""
    for ci, (heading, items) in enumerate(STACK):
        x = 26 + ci * col_w
        out += (
            f'<text x="{x:.1f}" y="72" fill="{MUTED}" font-size="10.5" '
            f'font-family="{MONO}" letter-spacing="1.8">{heading}</text>'
        )
        for ri, (name, slug, color) in enumerate(items):
            y = 72 + 26 + ri * row_h
            glyph = icon(slug, x, y - 14, 19)
            swatch = (
                ""
                if glyph
                else f'<rect x="{x + 4}" y="{y - 10}" width="11" height="11" rx="3" fill="{for_dark(color)}" />'
            )
            out += (
                f'<g class="tx" style="animation-delay:{0.025 * (ci * 3 + ri):.2f}s">'
                f'{plate(x, y - 14, 19, 5)}{glyph}{swatch}'
                f'<text x="{x + 30:.1f}" y="{y:.1f}" fill="{INK}" font-size="13.5" '
                f'font-family="{SANS}">{name}</text></g>'
            )

    body = f'''{frame(STACK_W, height, "LEGEND &#183; TECHNOLOGY", "map key")}
  {out}
  {outline(STACK_W, height)}'''
    return doc(STACK_W, height, "technology legend", body)


def main():
    user = fetch()
    weeks, _, _ = weekly(user)
    field = build_field(weeks)

    os.makedirs(OUT_DIR, exist_ok=True)
    cards = {
        "header.svg": render_header(user, field),
        "stack.svg": render_stack(),
        "languages.svg": render_languages(user),
        "stats.svg": render_stats(user),
        "activity.svg": render_activity(user),
        "footer.svg": render_footer(field),
    }
    for name, svg in cards.items():
        with open(os.path.join(OUT_DIR, name), "w", encoding="utf-8") as f:
            f.write(svg)
        print(f"wrote {name} ({len(svg):,} bytes)")


if __name__ == "__main__":
    main()
