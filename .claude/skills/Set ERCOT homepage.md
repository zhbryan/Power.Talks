---
name: Set-ERCOT-Homepage
description: Use when asked to set up, update, refresh, or extend the ERCOT homepage (the market-home landing view) in the Power.Talks web app — the About/intro copy, the Quick Access navigation tiles, or the "Quick runs" right-panel Artifacts (ERCOT major milestones timeline, ERCOT stakeholder process org chart) that inject into the content window.
trigger: When the user asks to update the ERCOT homepage, change the ERCOT intro text or quick-access links, add/edit/remove a right-panel artifact for the ERCOT home, or change how those artifacts appear in the content window.
---

# Set ERCOT Homepage

## Overview

The **ERCOT homepage** is the app's default landing view — the `market-home`
section, shown when `activeMarket === "ERCOT"`. It renders the `ERCOTHome`
component (About ERCOT copy, a Market Rules & Stakeholder Process blurb, and a
3×2 grid of "Quick Access" tiles that navigate to the other sections). Its
right panel is titled **Quick runs** and, on this view only, shows an
**Artifacts** tab listing two generated artifacts that inject into the content
window when clicked:

- **ERCOT major milestones timeline** → an iframe of `ERCOT Major Milestones.html`
- **ERCOT stakeholder process org chart** → the native `ErcotOrgChart` React panel

Open via **http://localhost/Power.Talks/html/Power.Talks%20home%20page.html** —
never `file://` (the milestones iframe and other data are fetched from WAMP at
runtime).

## File Map

| File | Role |
|---|---|
| `html/Power.Talks home page.html` | **Standalone bundle** served to the browser. Every `src/*.jsx` is embedded gzip+base64 in a `__bundler/manifest` script tag. Source edits do NOT appear until rebundled. |
| `html/rebuild_standalone.py` | Re-embeds every `src/*.jsx` into the bundle. Run after any src edit. Writes a `.bak` backup. Reports the entry count updated (11 as of June 2026). |
| `html/src/illustration.jsx` | **`ERCOTHome` component** (`window.ERCOTHome`): the homepage content — header, `About ERCOT` intro, `Market Rules & Stakeholder Process` blurb, and the `LINKS` Quick Access grid. This is the file to edit for homepage *copy*. |
| `html/src/rightpanel.jsx` | **`ERCOT_HOME_ARTIFACTS`** array (the Artifacts-tab cards for this view) and the `isErcotHome` branch that swaps the artifact list, forces the **Artifacts** tab, and hides the **For the talk** tab. |
| `html/src/app.jsx` | Landing state (`activeSection` defaults to `"market-home"`), the `ARTIFACT_SRCS` / `ARTIFACT_COMPONENTS` maps, the `onArtifactClick` injector, and the content-window render of `injectedPanels` (scoped to `market-home`). |
| `html/ERCOT Major Milestones.html` | The standalone page loaded by the `ercot-a1` iframe artifact. |
| `html/src/meetingtracks.jsx` | Defines `ErcotOrgChart` (`window.ErcotOrgChart`), the native panel used by the `ercot-a2` artifact. |

## Editing the homepage content (copy + nav)

All in `ERCOTHome` (`illustration.jsx`):

- **Header** — the `<h1>ERCOT</h1>` and subtitle.
- **Intro sections** — the two `pt-ercot-intro` blocks (`About ERCOT`, then
  `Market Rules & Stakeholder Process`). Edit the `pt-ercot-intro-eye` label
  and the `pt-ercot-intro-body` paragraph. Add another block by cloning a
  `pt-ercot-intro` div and adding an `<hr className="pt-ercot-intro-divider"/>`
  between blocks.
- **Quick Access tiles** — the `LINKS` array: `{ id, icon, label, desc }`.
  `id` must be a real section id (`paper-trails`, `meeting-tracks`,
  `hot-topics`, `daily-headlines`, `stats-illustrated`, `gallery`) — clicking a
  tile calls `onSectionChange(id)`. `icon` must exist on `window.I` (see
  `icons.jsx`).

`ERCOTHome` does **not** render the artifacts inline — they live only in the
right panel and inject on click. Keep it that way (see Common Mistakes).

## Editing the Quick runs right panel (Artifacts)

The Artifacts shown on the ERCOT home come from `ERCOT_HOME_ARTIFACTS` in
`rightpanel.jsx`. Each entry:

```js
{ id: "ercot-a1", title: "ERCOT major milestones timeline",
  desc: "…", icon: "Clock", tag: "History" }
```

`isErcotHome` (`ctx.section === "market-home"`) drives three things in
`RightPanel`: it swaps `activeArtifacts` to `ERCOT_HOME_ARTIFACTS`, forces the
**Artifacts** tab on open, and hides the **For the talk** tab. Don't remove
those — the ERCOT home has no per-issue "Quick runs" profile to show.

### How an artifact reaches the content window

`onArtifactClick` (`app.jsx`) dispatches by `id`:

| Map (in `app.jsx`) | Renders as | Current entry |
|---|---|---|
| `ARTIFACT_COMPONENTS` | a **native React panel** (`window[name]` at render time) | `"ercot-a2": "ErcotOrgChart"` |
| `ARTIFACT_SRCS` | an **injected iframe** with self-refitting height | `"ercot-a1": "/Power.Talks/html/ERCOT%20Major%20Milestones.html"` |

Two invariants — keep both:

1. **Once per session, and only on the ERCOT homepage.** `onArtifactClick`
   dedupes on `comp`/`src` in `injectedPanels` (a repeat click adds nothing),
   and the content-window render is gated by
   `activeSection === "market-home" && injectedPanels.map(...)`, so the panels
   never bleed into Paper Trails or other sections. A page reload starts a
   fresh session.
2. **iframe paths carry the `/Power.Talks` prefix** — the app is served under
   `localhost/Power.Talks/`, so a bare `/html/...` URL 404s.

An artifact `id` present in neither map falls through to `onRunPrompt` (just
pre-fills the composer draft) — that's the default for non-injecting items.

### Adding a new ERCOT-home artifact

1. **rightpanel.jsx** — add an entry to `ERCOT_HOME_ARTIFACTS` (unique `id`,
   `title`, `desc`, `icon` from `window.I`, `tag`).
2. **app.jsx** — wire the `id`:
   - native React panel → add to `ARTIFACT_COMPONENTS` (`id: "ComponentName"`)
     and make sure that component is defined and assigned to `window` in some
     bundled `src/*.jsx`.
   - injected page → add to `ARTIFACT_SRCS` (`id: "/Power.Talks/html/<page>.html"`),
     and place the page under `html/` (put generated standalone pages there).
3. Rebundle and verify.

## Rebuild & Verify

1. `python "html/rebuild_standalone.py"` — must report all source files updated.
2. Hard-refresh (Ctrl+F5) `http://localhost/Power.Talks/html/Power.Talks%20home%20page.html`.
3. The ERCOT homepage should be the landing view; the right panel opens on the
   **Artifacts** tab. Click each artifact: it appears once in the content
   window and scrolls into view; a second click does nothing.
4. Navigate to another section (e.g. a Quick Access tile) and confirm the
   injected artifacts do **not** appear there; return to ERCOT home and confirm
   they're still present.

## Common Mistakes

| Mistake | Fix |
|---|---|
| Editing `src/*.jsx` and expecting the page to change | The served page is a frozen bundle — always run `html/rebuild_standalone.py` afterwards |
| Opening via `file://` | The milestones iframe fails — use `http://localhost` (WAMP must be running) |
| Rendering the artifacts inline in `ERCOTHome` | They are click-injected via the right panel; inlining them double-shows them alongside the injected panel |
| Bare `/html/...` iframe src | Must be `/Power.Talks/html/...` or it 404s |
| Removing the `market-home` gate on `injectedPanels` | The artifacts then bleed into every section's content window |
| Dropping the `isErcotHome` tab logic | The ERCOT home would show an empty "For the talk" tab (no per-issue profile exists for it) |
| Quick Access `id` that isn't a real section | The tile navigates nowhere — use a valid `activeSection` id |
| `icon` not on `window.I` | Renders blank — add the icon to `icons.jsx` or pick an existing one |
