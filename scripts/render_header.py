"""Renders assets/header.svg: a topographic map whose elevation field is built
from the last year of contributions, so the terrain is unique to the account."""

import hashlib
import json
import math
import os
import urllib.request

USERNAME = os.environ.get("GITHUB_USER", "Dhruv-413")
TOKEN = os.environ["GITHUB_TOKEN"]
OUT_PATH = os.environ.get("OUT_PATH", "assets/header.svg")

WIDTH, HEIGHT = 1200, 320
COLS, ROWS = 176, 50
LEVELS = 15

INK = "#f8f8f2"
MUTED = "#8b90b8"
LOW = (68, 71, 90)
MID = (189, 147, 249)
HIGH = (255, 121, 198)

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { contributionCount } }
      }
    }
  }
}
"""


def fetch_weeks():
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
    with urllib.request.urlopen(req, timeout=30) as resp:
        cal = json.load(resp)["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    weeks = [sum(d["contributionCount"] for d in w["contributionDays"]) for w in cal["weeks"]]
    return weeks, cal["totalContributions"]


def jitter(index, salt):
    digest = hashlib.sha256(f"{USERNAME}:{salt}:{index}".encode()).digest()
    return int.from_bytes(digest[:4], "big") / 0xFFFFFFFF


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
        x_lo, x_hi = max(0, int(cx - 4 * sx)), min(COLS, int(cx + 4 * sx) + 1)
        y_lo, y_hi = max(0, int(cy - 4 * sy)), min(ROWS, int(cy + 4 * sy) + 1)
        for r in range(y_lo, y_hi):
            dy = (r - cy) / sy
            for c in range(x_lo, x_hi):
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

            def top():
                return (c + (level - a) / (b - a), r) if b != a else (c, r)

            def right():
                return (c + 1, r + (level - b) / (e - b)) if e != b else (c + 1, r)

            def bottom():
                return (c + (level - d) / (e - d), r + 1) if e != d else (c, r + 1)

            def left():
                return (c, r + (level - a) / (d - a)) if d != a else (c, r)

            if idx in (1, 14):
                segs.append((left(), top()))
            elif idx in (2, 13):
                segs.append((top(), right()))
            elif idx in (3, 12):
                segs.append((left(), right()))
            elif idx in (4, 11):
                segs.append((right(), bottom()))
            elif idx in (6, 9):
                segs.append((top(), bottom()))
            elif idx in (7, 8):
                segs.append((left(), bottom()))
            elif idx == 5:
                segs.append((left(), top()))
                segs.append((right(), bottom()))
            elif idx == 10:
                segs.append((top(), right()))
                segs.append((left(), bottom()))
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
                if direction == 0:
                    pts.append(far)
                else:
                    pts.insert(0, far)
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
        if closed:
            out.append(out[0])
        else:
            out.append(pts[-1])
        pts = out
    return pts


def to_path(pts):
    sx = WIDTH / (COLS - 1)
    sy = HEIGHT / (ROWS - 1)
    head = f"M{pts[0][0] * sx:.1f} {pts[0][1] * sy:.1f}"
    tail = "".join(f"L{x * sx:.1f} {y * sy:.1f}" for x, y in pts[1:])
    return head + tail


def ramp(t):
    if t < 0.5:
        u = t / 0.5
        a, b = LOW, MID
    else:
        u = (t - 0.5) / 0.5
        a, b = MID, HIGH
    return "#%02x%02x%02x" % tuple(round(a[i] + (b[i] - a[i]) * u) for i in range(3))


def summits(field, weeks):
    peak = max(weeks) or 1
    span = max(len(weeks) - 1, 1)
    marks = []
    ranked = sorted(range(len(weeks)), key=lambda i: weeks[i], reverse=True)[:6]
    for i in ranked:
        if weeks[i] <= 0:
            continue
        x = i / span * WIDTH
        y = (0.28 + 0.46 * jitter(i, "y")) * HEIGHT
        marks.append((x, y, 0.55 + 0.45 * (weeks[i] / peak)))
    return marks


def build_svg(field, weeks, total):
    layers = []
    for li in range(1, LEVELS):
        level = li / LEVELS
        paths = chain(marching_squares(field, level))
        if not paths:
            continue
        t = li / (LEVELS - 1)
        color = ramp(t)
        opacity = 0.32 + 0.50 * t
        width = 0.9 + 0.9 * t
        delay = 0.15 + t * 0.9
        body = "".join(
            f'<path d="{to_path(chaikin(p))}" pathLength="1" '
            f'style="animation-delay:{delay:.2f}s" />'
            for p in paths
        )
        layers.append(
            f'<g class="ln" fill="none" stroke="{color}" stroke-width="{width:.2f}" '
            f'stroke-opacity="{opacity:.2f}" stroke-linecap="round" '
            f'stroke-linejoin="round">{body}</g>'
        )

    dots = "".join(
        f'<circle class="pk" cx="{x:.1f}" cy="{y:.1f}" r="{2.0 + 1.6 * s:.1f}" '
        f'fill="#8be9fd" style="animation-delay:{0.9 + 0.12 * i:.2f}s" />'
        for i, (x, y, s) in enumerate(summits(field, weeks))
    )

    return f'''<svg width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{USERNAME} contribution terrain">
  <defs>
    <radialGradient id="g1" cx="18%" cy="26%" r="62%">
      <stop offset="0%" stop-color="#bd93f9" stop-opacity="0.30" />
      <stop offset="100%" stop-color="#bd93f9" stop-opacity="0" />
    </radialGradient>
    <radialGradient id="g2" cx="76%" cy="72%" r="60%">
      <stop offset="0%" stop-color="#ff79c6" stop-opacity="0.26" />
      <stop offset="100%" stop-color="#ff79c6" stop-opacity="0" />
    </radialGradient>
    <radialGradient id="g3" cx="52%" cy="8%" r="52%">
      <stop offset="0%" stop-color="#8be9fd" stop-opacity="0.16" />
      <stop offset="100%" stop-color="#8be9fd" stop-opacity="0" />
    </radialGradient>
    <linearGradient id="scrim" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#12131c" stop-opacity="0.82" />
      <stop offset="40%" stop-color="#12131c" stop-opacity="0.46" />
      <stop offset="72%" stop-color="#12131c" stop-opacity="0" />
    </linearGradient>
    <radialGradient id="halo" cx="23%" cy="52%" r="44%">
      <stop offset="0%" stop-color="#12131c" stop-opacity="0.88" />
      <stop offset="58%" stop-color="#12131c" stop-opacity="0.55" />
      <stop offset="100%" stop-color="#12131c" stop-opacity="0" />
    </radialGradient>
    <filter id="grain" x="0" y="0" width="100%" height="100%">
      <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="3" />
      <feColorMatrix type="saturate" values="0" />
    </filter>
    <clipPath id="frame">
      <rect x="0" y="0" width="{WIDTH}" height="{HEIGHT}" rx="16" />
    </clipPath>
    <style>
      @keyframes draw {{ to {{ stroke-dashoffset: 0; }} }}
      @keyframes rise {{ from {{ opacity: 0; transform: translateY(10px); }} to {{ opacity: 1; transform: translateY(0); }} }}
      @keyframes glow {{ 0%, 100% {{ opacity: 0.35; }} 50% {{ opacity: 1; }} }}
      .ln path {{ stroke-dasharray: 1; stroke-dashoffset: 1; animation: draw 2.2s ease-out forwards; }}
      .pk {{ opacity: 0; animation: glow 3.4s ease-in-out infinite; }}
      .tx {{ opacity: 0; animation: rise 0.7s cubic-bezier(.2,.7,.3,1) forwards; }}
    </style>
  </defs>

  <g clip-path="url(#frame)">
    <rect width="{WIDTH}" height="{HEIGHT}" fill="#12131c" />
    <rect width="{WIDTH}" height="{HEIGHT}" fill="url(#g1)" />
    <rect width="{WIDTH}" height="{HEIGHT}" fill="url(#g2)" />
    <rect width="{WIDTH}" height="{HEIGHT}" fill="url(#g3)" />
    {"".join(layers)}
    {dots}
    <rect width="{WIDTH}" height="{HEIGHT}" fill="url(#scrim)" />
    <rect width="{WIDTH}" height="{HEIGHT}" fill="url(#halo)" />
    <rect width="{WIDTH}" height="{HEIGHT}" filter="url(#grain)" opacity="0.05" />

    <g class="tx" style="animation-delay:0.15s">
      <text x="64" y="132" fill="{INK}" font-size="54" font-weight="700" letter-spacing="2"
            font-family="Segoe UI, Helvetica Neue, Helvetica, Arial, sans-serif">Dhruv Gupta</text>
    </g>
    <g class="tx" style="animation-delay:0.30s">
      <text x="66" y="170" fill="#ff79c6" font-size="19" font-weight="600" letter-spacing="1.4"
            font-family="Segoe UI, Helvetica Neue, Helvetica, Arial, sans-serif">Machine Learning &#183; Full&#8209;Stack Engineering</text>
    </g>
    <g class="tx" style="animation-delay:0.45s">
      <text x="66" y="214" fill="{MUTED}" font-size="13.5" letter-spacing="0.3"
            font-family="SFMono-Regular, Consolas, Liberation Mono, Menlo, monospace">terrain mapped from {total:,} contributions this year</text>
    </g>
  </g>
  <rect x="0.75" y="0.75" width="{WIDTH - 1.5}" height="{HEIGHT - 1.5}" rx="16" fill="none"
        stroke="#3b3d54" stroke-width="1.5" />
</svg>
'''


def main():
    weeks, total = fetch_weeks()
    field = build_field(weeks)
    svg = build_svg(field, weeks, total)
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(svg)


if __name__ == "__main__":
    main()
