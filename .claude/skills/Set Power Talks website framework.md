---
name: Set-Power-Talks-Website-Framework
description: Use when working on the Power.Talks web front-end at the architecture level — understanding or changing the app shell, the JSX bundle/rebuild pipeline, the window-globals module contract, app state and section routing, the right panel, theming/tweaks, or how static vs live data flows. Start here before any UI change; defer to the per-homepage skills for content within a section.
trigger: When the user asks to set up, explain, extend, or debug the Power.Talks website framework, the bundler, the React app shell, the src/*.jsx module structure, section routing, theming, or how the front-end is wired together — as opposed to editing one specific homepage's content.
---

# Set Power.Talks Website Framework

## What this is

The Power.Talks front-end is a **single-page React app with no build step**.
React 18 (UMD) and Babel Standalone are loaded from a CDN and compile the JSX
**in the browser**. There is no npm, webpack, or bundler toolchain — modules are
plain `src/*.jsx` files that attach their exports to `window`, and a small
Python script packs them into one self-contained HTML file for serving.

Two delivery forms of the same app:

| Form | File | Use |
|---|---|---|
| **Dev (unpacked)** | `html/archive/index.html` | Loads each `src/*.jsx` live via `<script type="text/babel" src=...>`. Edit-and-refresh, no rebuild — but artifact/data paths still need WAMP. |
| **Served (bundle)** | `html/Power.Talks home page.html` | The production page. Every `src/*.jsx` is embedded gzip+base64 in a `__bundler/manifest` script tag and unpacked by an inline loader at runtime. **Source edits do NOT appear until rebundled.** |

Open via **http://localhost/Power.Talks/html/Power.Talks%20home%20page.html** —
never `file://` (live JSON and the milestones iframe are fetched from WAMP).

## Tech stack

- **React 18.3.1 UMD** + **ReactDOM** + **@babel/standalone 7.29.0**, all from
  `unpkg.com` (see `archive/index.html` for the exact pinned URLs + SRI hashes).
- **No JSX build** — `<script type="text/babel">` blocks are compiled client-side.
  This is why every module is a flat script that assigns to `window`, not an ES
  module with `import`/`export`.
- **Styling**: CSS custom properties on `:root` (and `[data-theme="dark"]`),
  defined once in the page `<head>`. Components use inline `<style>` tags
  scoped by class prefix (`pt-*`). Key vars: `--bg`, `--panel`, `--ink`,
  `--ink-2`, `--muted`, `--rule`/`--rule-2`, `--accent`/`--accent-2`/`--accent-soft`,
  `--ok`, `--warn`, `--sans` (Inter Tight), `--serif` (Instrument Serif),
  `--mono` (JetBrains Mono).
- **Mount**: `app.jsx` ends with `ReactDOM.createRoot(document.getElementById("root")).render(<App/>)`.

## The bundle pipeline

```
src/*.jsx  ──(rebuild_standalone.py)──►  Power.Talks home page.html
   edit                                   (served bundle; .bak written)
```

- `html/rebuild_standalone.py` reads every `src/*.jsx`, gzip+base64-encodes it,
  and replaces the matching entry inside the bundle's `__bundler/manifest`
  JSON. It matches entries by **content fingerprint** (first 80 chars) **or** a
  stable **anchor string** per file (`ANCHORS` dict — e.g. `app.jsx` →
  `ReactDOM.createRoot`, `data.jsx` → `window.DATA = {`). It must report **all
  source files updated (11 entries)**; a lower count means an anchor stopped
  matching — fix the anchor, don't ship a partial bundle.
- The bundle's inline loader (top of the HTML `<body>`) decodes the manifest,
  injects each module as a `text/babel` script in order, then Babel compiles
  them. A `#__bundler_thumbnail` SVG + "Unpacking…" indicator show during load;
  a red `#__bundler_err` strip surfaces runtime errors.
- **Always run the rebuild after any `src/*.jsx` edit**, then hard-refresh
  (Ctrl+F5) — the served page is otherwise frozen.

## Module map & load order

Scripts load in this order (dependencies first). Each assigns globals on
`window`; **load order matters** because modules read each other's globals at
call time:

| # | File | Exports (`window.*`) | Role |
|---|---|---|---|
| 1 | `src/icons.jsx` | `I`, `Icon` | SVG icon set. `I[name]` is used everywhere — every `icon:` field must be a key here. |
| 2 | `src/data.jsx` | `DATA` | All **static** data: `MESSAGES`, `SUGGESTED_RUNS`, `ARTIFACTS`, `CATEGORY_INTROS`, `CONTEXTUAL_RUNS`, `CURRENT_TALK_*`, and the `<CAT>_<STATUS>` rule-list arrays. |
| 3 | `src/illustration.jsx` | `TalkIllustration`, `Waveform`, `PaperTrailsIllustration`, `PAPER_TRAIL_CODES`, `FOLDER_PATHS`, `ERCOTHome` | Center-pane "illustrations" — the per-section main content, incl. the ERCOT homepage and the Paper Trails category grid/homepages/detail views. |
| 4 | `src/meetingtracks.jsx` | `MeetingTracksOrgChart`, `ErcotOrgChart` | Org-chart panels (Meeting Tracks section; `ErcotOrgChart` is also an ERCOT-home artifact). |
| 5 | `src/sidebar.jsx` | `Sidebar` | Left rail: ISO market switcher, section nav, recents. |
| 6 | `src/topbar.jsx` | `Topbar` | Header: breadcrumb, nav, right-panel toggle, home (logo) action. |
| 7 | `src/messages.jsx` | `MessageStream`, `UserMsg`, `AssistantAnalysis` | The scrollable conversation column that wraps the active illustration. |
| 8 | `src/composer.jsx` | `Composer` | Bottom input box (the "Ask me anything about ERCOT…" prompt). |
| 9 | `src/rightpanel.jsx` | `RightPanel` | "Quick runs" right panel — per-issue profile cards, category intro card, Artifacts tab. |
| 10 | `src/tweaks.jsx` | `TweaksPanel`, `applyTweaksToRoot` | Theme/accent/layout tweak UI + the function that writes CSS vars to `:root`. |
| 11 | `src/app.jsx` | (mounts `App`) | Top-level state, layout grid, section routing, wires every component together. |

**Module contract:** components reference each other as `window.X` (e.g.
`window[p.comp]`, `I[name]`, `window.DATA`). When adding a module, place its
`<script>` before any module that uses its globals, and register it in
`rebuild_standalone.py`'s `ANCHORS` with a unique stable string.

## App shell (`app.jsx`)

`App()` holds all state and renders a CSS-grid shell:

```
grid-template-areas:  "side top   top"
                      "side main  right"
```

- **`<Sidebar>`** (`side`) — `onMarketChange` sets `activeMarket` + jumps to the
  `market-home` section; `onSectionChange` switches sections.
- **`<Topbar>`** (`top`) — `onToggleRight` toggles `rightOpen`; `onHome` returns
  to `market-home` (note: the clickable ERCOT logo only renders **while on**
  `market-home`, so use the sidebar market switcher to return from elsewhere).
- **`.pt-main-col`** (`main`) — `<MessageStream>` wrapping the active
  illustration (the section router), plus injected artifact panels, plus the
  `<Composer>`.
- **`<RightPanel>`** (`right`) — receives a `context` object describing the
  current selection.

### Section routing

`activeSection` (defaults to **`"market-home"`**) selects the center
illustration:

| `activeSection` | Illustration |
|---|---|
| `market-home` | `<ERCOTHome>` (the default landing view) |
| `paper-trails` | `<PaperTrailsIllustration>` |
| `meeting-tracks` | `<MeetingTracksOrgChart>` |
| anything else (`hot-topics`, `daily-headlines`, `stats-illustrated`, `gallery`) | `<TalkIllustration>` (placeholder) |

Selection state is per-domain: `activeMarket`, `activePaperCode`,
`activeMeetingNode`, and one `active<Cat>` (NPRR/COPMGRR/PGRR/SCR/NOGRR/RMGRR)
each reset by an effect when the section/category changes.

### Right panel & injected artifacts

`RightPanel` reads `context={{ section, code, node, nprr, copmgrr, pgrr, scr,
nogrr, rmgrr }}`. It shows two tabs — **"For the talk"** (per-issue Quick-runs
profile, or the category intro card) and **"Artifacts"**. `isErcotHome`
(`section === "market-home"`) swaps in `ERCOT_HOME_ARTIFACTS`, forces the
Artifacts tab, and hides "For the talk".

Artifacts that open in the center window go through `onArtifactClick` in
`app.jsx`: `ARTIFACT_COMPONENTS` (native React panel via `window[name]`) or
`ARTIFACT_SRCS` (self-fitting iframe). Injected panels are **deduped** (once per
session) and **gated to `activeSection === "market-home"`** so they don't bleed
into other sections. See the **Set-ERCOT-Homepage** skill for details.

## Theming & edit mode (`tweaks.jsx`)

- Defaults live in `window.POWER_TALKS_TWEAKS` (an `/*EDITMODE-BEGIN*/…/*END*/`
  block in the page) — `theme`, `accent`, `sidebar`, `rightPanel`, `typePair`.
  `App` seeds state from it and calls `applyTweaksToRoot(tweaks)` to write CSS
  vars / `data-theme` on `:root`.
- The host (a parent frame) drives an **edit mode** over `postMessage`:
  `__activate_edit_mode` / `__deactivate_edit_mode` toggle the `TweaksPanel`;
  `setTweak` echoes changes back via `__edit_mode_set_keys`. Leave this wiring
  intact when touching `App`.

## Data: static vs live

| Kind | Source | Changes need |
|---|---|---|
| **Static** | `data.jsx` → `window.DATA` (lists, messages, suggested runs, category intros) | Edit/regenerate `data.jsx`, then **rebundle**. |
| **Live per-issue** | `fetch()` from WAMP at `/Power.Talks/Documents%20Database/ERCOT.MKT.RULES/<CAT>/<ID>/Quick%20runs/<ID>%20{Profile,Summary}.json` | Just regenerate the JSON — no rebuild. URLs are %-encoded; COPMGRR IDs zero-pad to 3 digits. |

The rule-list arrays in `data.jsx` are generated from issue profiles — see the
**Set-Paper-Trails-Homepage** skill for the regen + splice tooling.

## The golden workflow

1. Edit `html/src/*.jsx` (or `data.jsx`).
2. `python "html/rebuild_standalone.py"` → must report **11 entries updated**;
   writes a `.bak`.
3. Hard-refresh (Ctrl+F5) `http://localhost/Power.Talks/html/Power.Talks%20home%20page.html`.
4. Verify by driving the real page (Playwright/browser), not by reading source.

## Related skills

- **Set-ERCOT-Homepage** — the `market-home` landing view + its Artifacts.
- **Set-Paper-Trails-Homepage** — the `paper-trails` category grid, homepages,
  detail views, Quick-runs cards, and the list-data regeneration pipeline.
- **Set-Paper-Trails-Category-homepage** / **Item-Rule-homepage** — finer-grained
  category/issue views.

## Common Mistakes

| Mistake | Fix |
|---|---|
| Editing `src/*.jsx` and expecting the page to change | The served page is a frozen bundle — run `html/rebuild_standalone.py` |
| `rebuild_standalone.py` reports < 11 updated | An `ANCHORS` string no longer matches that file — update the anchor |
| Opening via `file://` | Live JSON + the milestones iframe fail — use `http://localhost` (WAMP running) |
| Using ES `import`/`export` in a `src/*.jsx` | There is no module bundler — assign to `window` and order the `<script>` accordingly |
| New module's globals are `undefined` at use | Its `<script>` loads after a consumer — move it earlier; register it in `ANCHORS` |
| `icon:` value not a key of `window.I` | Renders blank — add it to `icons.jsx` or pick an existing icon |
| Hardcoding a section's content in `app.jsx` | Put center content in an illustration component (`illustration.jsx`/`meetingtracks.jsx`) and route it via `activeSection` |
| Bare `/html/...` artifact/iframe path | Must carry the `/Power.Talks` prefix or it 404s under `localhost/Power.Talks/` |
| Stale browser cache after rebundle | Hard-refresh (Ctrl+F5) — the bundle is one big HTML file |
