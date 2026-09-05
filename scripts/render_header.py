import html

WIDTH, HEIGHT = 1200, 300
BG = "#1e1f29"
PANEL_BORDER = "#3b3d54"
GUTTER = "#4b4d6b"
COMMENT = "#6272a4"
FG = "#f8f8f2"
KEYWORD = "#ff79c6"
VAR = "#8be9fd"
STRING = "#f1fa8c"
GREEN = "#50fa7b"
RED = "#ff5555"
PURPLE = "#bd93f9"

FONT = "SFMono-Regular, Consolas, 'Liberation Mono', Menlo, monospace"

LINE_HEIGHT = 32
CODE_TOP = 88
GUTTER_X = 52
CODE_X = 78
FONT_SIZE = 18


def esc(s):
    return html.escape(s, quote=False)


def line_tspans(parts):
    return "".join(f'<tspan fill="{color}">{esc(text)}</tspan>' for text, color in parts)


LINES = [
    [("const ", KEYWORD), ("dhruv", VAR), (" = {", FG)],
    [("  name", FG), (": ", FG), ('"Dhruv Gupta"', STRING), (",", FG)],
    [("  role", FG), (": ", FG), ('"Machine Learning + Full-Stack"', STRING), (",", FG)],
    [("  studying", FG), (": ", FG), ('"CSE, IoT and Intelligent Systems"', STRING), (",", FG)],
    [("  focus", FG), (": [", FG), ('"React"', STRING), (", ", FG), ('"Python"', STRING), (", ", FG), ('"Systems Design"', STRING), ("],", FG)],
    [("  status", FG), (": ", FG), ('"open_to_work"', GREEN), (",", FG)],
    [("};", FG)],
]


def build():
    rows = []
    for i, parts in enumerate(LINES):
        y = CODE_TOP + i * LINE_HEIGHT
        delay = 0.08 + i * 0.09
        rows.append(
            f'<text class="line" style="animation-delay:{delay:.2f}s" '
            f'x="{GUTTER_X}" y="{y}" fill="{GUTTER}" font-size="{FONT_SIZE}" '
            f'font-family="{FONT}" text-anchor="end">{i + 1}</text>'
        )
        rows.append(
            f'<text class="line" style="animation-delay:{delay:.2f}s" '
            f'x="{CODE_X}" y="{y}" font-size="{FONT_SIZE}" font-family="{FONT}" '
            f'xml:space="preserve">{line_tspans(parts)}</text>'
        )

    status_line_y = CODE_TOP + 5 * LINE_HEIGHT
    status_dot_x = CODE_X + 26 * FONT_SIZE * 0.605 + 16
    cursor_x = CODE_X + 2 * FONT_SIZE * 0.605
    cursor_y = CODE_TOP + 6 * LINE_HEIGHT

    svg = f'''<svg width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <radialGradient id="glow" cx="80%" cy="15%" r="75%">
      <stop offset="0%" stop-color="{PURPLE}" stop-opacity="0.35" />
      <stop offset="100%" stop-color="{PURPLE}" stop-opacity="0" />
    </radialGradient>
    <clipPath id="panelClip">
      <rect x="1" y="1" width="{WIDTH - 2}" height="{HEIGHT - 2}" rx="14" />
    </clipPath>
    <style>
      @keyframes fadeSlide {{ from {{ opacity: 0; transform: translateX(-8px); }} to {{ opacity: 1; transform: translateX(0); }} }}
      @keyframes blink {{ 0%, 49% {{ opacity: 1; }} 50%, 100% {{ opacity: 0; }} }}
      @keyframes pulse {{ 0%, 100% {{ opacity: 1; }} 50% {{ opacity: 0.25; }} }}
      .line {{ opacity: 0; animation: fadeSlide 0.45s ease forwards; }}
      .cursor {{ animation: blink 1s steps(1) infinite; }}
      .status-dot {{ animation: pulse 1.8s ease-in-out infinite; }}
    </style>
  </defs>

  <g clip-path="url(#panelClip)">
    <rect x="0" y="0" width="{WIDTH}" height="{HEIGHT}" fill="{BG}" />
    <rect x="0" y="0" width="{WIDTH}" height="{HEIGHT}" fill="url(#glow)" />
  </g>
  <rect x="1" y="1" width="{WIDTH - 2}" height="{HEIGHT - 2}" rx="14" fill="none" stroke="{PANEL_BORDER}" stroke-width="1.5" />

  <line x1="0" y1="40" x2="{WIDTH}" y2="40" stroke="{PANEL_BORDER}" stroke-width="1" />
  <circle cx="28" cy="20" r="6" fill="{RED}" />
  <circle cx="50" cy="20" r="6" fill="{STRING}" />
  <circle cx="72" cy="20" r="6" fill="{GREEN}" />
  <text x="96" y="25" fill="{COMMENT}" font-size="14" font-family="{FONT}">dhruv.ts</text>
  <text x="{WIDTH - 24}" y="25" fill="{COMMENT}" font-size="13" font-family="{FONT}" text-anchor="end">~/profile</text>

  {"".join(rows)}

  <circle class="status-dot" cx="{status_dot_x:.0f}" cy="{status_line_y - 5:.0f}" r="4" fill="{GREEN}" />
  <text class="cursor" x="{CODE_X + 5 * FONT_SIZE * 0.605:.0f}" y="{cursor_y}" fill="{FG}" font-size="{FONT_SIZE}" font-family="{FONT}">&#9608;</text>
</svg>
'''
    return svg


if __name__ == "__main__":
    with open("assets/header.svg", "w", encoding="utf-8") as f:
        f.write(build())
