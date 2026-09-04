# Live profile README — design

**Date:** 2026-09-05
**Repo:** `Dhruv-413/Dhruv-413` (GitHub profile README)
**Approach:** C — hybrid. Live charts from a self-hosted Vercel endpoint, cached at the edge, with the committed-asset workflow retained as a working fallback.

---

## 1. Goal

Nothing on the page should be hand-typed where an API knows the answer. The page should also look like one designed dashboard rather than a wall of borrowed stickers.

Those two goals pull against each other, and resolving that tension is the main design decision in this document. See section 5.

## 2. Constraints

Findings, not preferences. Each closes off an option that would otherwise look attractive.

| # | Constraint | Consequence |
| :-- | :-- | :-- |
| C1 | GitHub serves static markdown; nothing executes at view time. | "Live" is only reachable via a hosted image endpoint or a scheduled Action that commits files. |
| C2 | Camo honours the origin's `Cache-Control`. The public github-readme-stats instance clamps to a 24h minimum; self-hosting removes the clamp. | We control freshness only if we own the origin. |
| C3 | Vercel Hobby functions time out at 10s. The current rhythm chart issues 30 sequential GraphQL calls (~30s measured). | Commit history must collapse into a single batched query using GraphQL aliases. |
| C4 | An `<img>` cannot contain a link, and its text is invisible to search and screen readers. | Project links, credential tables and the toolkit stay markdown. Only charts become images. |
| C5 | A non-2xx response renders as a broken-image icon on the profile. | Every error path returns HTTP 200 with a valid fallback SVG. |
| C6 | An SVG loaded via `<img>` renders in secure-static mode: no scripts, no webfonts, no external refs. A `prefers-color-scheme` query inside it follows the reader's OS, not their GitHub theme. | System fonts only; one response per theme, selected by `<picture>`. |
| C7 | A PAT expires, and Vercel Hobby instances are known to pause. | The committed-asset path stays functional and swappable in one edit. |

## 3. Architecture

The central change: **the drawing code becomes a shared library** with two callers. It currently lives inside one script, and an HTTP endpoint cannot reuse it without duplicating it — which would guarantee the live charts and the fallback charts drift apart.

```text
lib/
  theme.py      palettes, fonts, geometry primitives      (moved from scripts/)
  github.py     GraphQL client + data shaping             (new; one batched query)
  cards.py      pure functions: shaped data -> SVG string  (extracted from build_readme.py)

api/
  card.py       Vercel handler. ?card=<name>&theme=<dark|light>

scripts/
  build_banner.py   static hero; imports lib/theme
  build_readme.py   workflow: markdown blocks + fallback SVGs; imports lib/*
  selftest.py       renders every card x theme from fixtures; asserts valid output

content/
  projects.json     curated Selected work copy; see section 6

vercel.json         routes api/card.py, includeFiles lib/**
```

`lib/cards.py` functions are pure: data in, SVG string out. No network, no filesystem, no clock. That is what makes them testable offline and byte-identical across both callers.

### Data flow

```text
GitHub GraphQL ──> lib/github.py ──> ProfileData ──┬──> lib/cards.py ──> SVG ──> HTTP 200        (live)
                   (1 batched query)               │
                                                   └──> lib/cards.py ──> SVG ──> assets/*.svg   (fallback)
                                                        build_readme.py ──> markdown blocks
```

## 4. Caching

Rate-limit protection is a requirement, so the edge does the work:

```text
Cache-Control: public, max-age=0, s-maxage=1800, stale-while-revalidate=86400
Content-Type:  image/svg+xml; charset=utf-8
```

- `s-maxage=1800` — Vercel's CDN serves the cached SVG for 30 minutes without invoking the function at all. Worst case is roughly **8 GraphQL calls per hour** across all six cards, against a 5,000/hour limit.
- `stale-while-revalidate=86400` — if the API is slow, rate-limited or down, the reader still gets yesterday's card instantly instead of a broken image, while a fresh one is fetched in the background.
- `max-age=0` keeps browsers from pinning their own copy, so the CDN stays the single source of freshness.

30 minutes is the deliberate compromise between "updates on refresh" and "never hits the rate limit". It is one constant, easy to lower later.

## 5. The clutter problem, and the decision that resolves it

The prevailing 2026 advice is to use *one* stats widget, not three stacked — profiles fail when they pile a streak counter, a trophy wall, an activity graph and a language bar together. That advice conflicts with the goal in section 1.

**Resolution: the clutter comes from mixing visual languages, not from having many charts.** Five widgets from five services means five palettes, five type stacks, five corner radii. Six charts drawn by *our own* `lib/cards.py` from one palette read as a designed dashboard.

So the rule for this repo is: **if a widget is worth having, we render it ourselves.** Consequences:

| Widget | Decision | Why |
| :-- | :-- | :-- |
| Trophy wall (`github-profile-trophy`) | **Rejected — build our own `milestones` card** | Theme-based, not per-colour; a true custom palette requires forking `src/theme.ts`. Free instances are known to pause. Its style would clash with the banner, and generic trophies rank low on a young account. Ours draws real figures: longest streak, busiest day, stars, languages, years active. |
| Activity graph (`github-readme-activity-graph`) | **Rejected — build our own `activity` card** | It does expose per-colour params, so it *could* be matched, but it is another live service dependency for a chart we can already draw. |
| Snake game (`Platane/snk`) | **Accepted** | The one exception that earns its place. It is an Action that commits an SVG — no service to go down — and `color_dots` takes exactly five colours, so it matches our contribution ramp precisely. Genuinely novel rather than decorative. |
| Visitor counters | **Rejected** | Not data about the work. |

### Card catalogue

All six rendered by us, all live through the endpoint:

| `?card=` | Content |
| :-- | :-- |
| `snapshot` | Headline figures: contributions, commits, PRs, streak, stars |
| `contributions` | 53-week heatmap |
| `activity` | Contribution trend over the year, as an area chart |
| `languages` | Language split, stacked bar |
| `rhythm` | 24-hour commit clock in IST |
| `milestones` | Real achievements, replacing the trophy wall |

Plus **snake** (committed by the `Platane/snk/svg-only@v3` Action, palette-matched, dark and light) and a **recent activity** markdown list generated by the workflow, because those entries need working links.

## 6. Coverage: what stops being hand-typed

**Selected work** becomes curated copy plus live metrics rather than fully generated.

The reason is concrete: `Eye-Gaze-Tracking-` and `Dhruv` have no GitHub description at all. Generating that section purely from the API would replace good writing with blank cells — freshness bought at the cost of quality.

So the prose lives in `content/projects.json`, and the workflow injects only the volatile fields — **stars, primary language, last-push date** — and drops any entry whose repo was deleted or made private.

**Newly generated:** `<!-- projects -->`, `<!-- recent -->`, plus the existing snapshot, languages and rhythm fallback tables.

**Deliberately hand-written:** About, Toolkit, experience, certifications. Judgement, not data.

## 7. Failure behaviour (C5)

| Failure | Response |
| :-- | :-- |
| `GH_PAT` unset in Vercel | 200 + "stats unavailable" card in the same visual language |
| GraphQL error, rate limit, timeout | Same fallback card, reason in `aria-label`; `stale-while-revalidate` usually serves the last good card instead |
| Unknown `card=` / `theme=` | Falls back to `snapshot` / `light` rather than erroring |

## 8. Workflow changes

- Cron every 6 hours (`0 */6 * * *`).
- Steps: `build_banner.py` → `build_readme.py` → `selftest.py` → snake Action → commit if changed.
- Uses `secrets.GH_PAT || secrets.GITHUB_TOKEN`, already wired.

## 9. Fallback switch (C7)

`build_readme.py` holds one constant. The Vercel domain is unknown until deploy; it is the only value in this design deferred to implementation.

```python
LIVE_BASE = "https://<app>.vercel.app/api/card"   # or "" to serve committed assets
```

Empty string rewrites the `<!-- graphs -->` block to point at `./assets/*.svg`. One edit, one workflow run, profile restored.

## 10. Testing

- **`scripts/selftest.py`** — renders all 6 cards x 2 themes from a checked-in fixture; asserts each parses as XML, carries a `viewBox`, contains no `None`/`NaN`/`Infinity`, and is non-trivial in length. No token needed; runs in CI.
- **Local visual harness** — renders every card into one page against GitHub's real dark and light canvas colours for eyeball review.
- **Deploy smoke test** — before the README points at the endpoint: confirm the Python runtime imports across `lib/`, and inspect the headers Camo actually receives.

## 11. Build order

Everything except the last step is independent of Vercel authentication, so it is built and verified first:

1. `lib/` refactor + the two new cards + selftest — fully verifiable offline.
2. Snake Action + workflow + markdown generation + committed fallbacks. **At this point the README is complete and correct with zero external dependencies.**
3. Vercel deploy, then flip `LIVE_BASE`. Requires the owner's account access.

## 12. Risks

| Risk | Mitigation |
| :-- | :-- |
| Vercel Python runtime cannot import across `lib/` | Smoke test before wiring. Fallback: shared modules move under `api/_lib/`. |
| Camo caches harder than the headers ask | Verified empirically after deploy. If so, keep the 6-hourly committed model and say so plainly rather than claiming live. |
| 10s timeout | Single batched query (C3); selftest measures query time. |
| PAT expiry / Vercel pause | Fallback card (§7) + one-line switch (§9) + committed assets that never stopped being generated. |

## 13. Security

The PAT is created and pasted into Vercel's dashboard **by the repo owner**. It never enters this repository, this document, or any commit. `GH_PAT` in Actions and the Vercel environment variable are two separate copies, each managed in its own dashboard.
