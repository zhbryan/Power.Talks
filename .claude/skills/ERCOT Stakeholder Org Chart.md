---
name: ERCOT Stakeholder Org Chart
description: Generates or regenerates html/ERCOT Stakeholder Org Chart.html — a standalone hierarchical organizational chart showing the ERCOT stakeholder revision review hierarchy, styled to match the Power.Talks design system.
trigger: When the user asks to generate, update, or rebuild the ERCOT stakeholder process org chart.
---

# ERCOT Stakeholder Org Chart — Generator

## Overview

This skill writes `html/ERCOT Stakeholder Org Chart.html` — a fully self-contained, standalone HTML/CSS file with no JavaScript. It renders a top-down hierarchical organizational chart showing the ERCOT revision review chain from regulatory authority down to working subcommittees.

---

## Output File

```
html/ERCOT Stakeholder Org Chart.html
```

Verify at: `http://localhost/Power.Talks/html/ERCOT%20Stakeholder%20Org%20Chart.html`

## In-App Copy — keep in sync

The Power.Talks content window renders this chart **natively** via the
`ErcotOrgChart` React component at the end of `html/src/meetingtracks.jsx`
(exported as `window.ErcotOrgChart`; routed from the Artifacts button through
`ARTIFACT_COMPONENTS` in `app.jsx`). It mirrors this skill's hierarchy with
`eoc-*` CSS classes and follows the app's light/dark theme automatically.

**Whenever the hierarchy, names, or sub-tiers change, update BOTH:** the
standalone HTML file (this skill's output) and the data arrays
(`EOC_BOARD_COMMITTEES`, `EOC_TAC_GROUPS`, `EOC_SUBS`) in the component —
then run `python "html/rebuild_standalone.py"` so the app bundle picks it up.

---

## Hierarchy Structure

```
PUCT  (Public Utility Commission of Texas — Regulatory Authority)
  │
Board of Directors  (ERCOT Board — Final Vote)
  │    └─ satellite: Board Committees — F&A, HR&G, T&S
  │
TAC  (Technical Advisory Committee — Reviews & Recommends)
  │    └─ satellite: TAC WGs & Task Forces — LLWG, CFSG, RTCBTF (winding down)
  │
  ├── PRS  (Protocol Revision Subcommittee)
  │     └─ (no standing working groups — drafting via PRS workshops)
  ├── ROS  (Reliability & Operations Subcommittee)
  │     └─ BSWG, DWG, IBRWG, MWG, NDSWG, OWG, OTWG, PDCWG, PLWG, SPWG, SSWG, VPWG
  ├── RMS  (Retail Market Subcommittee)
  │     └─ TDTMS, RMTTF
  └── WMS  (Wholesale Market Subcommittee)
        └─ CMWG, DSWG, SAWG, WMWG
```

> COPS no longer exists — it was absorbed into WMS. Do not re-add it.
> Parent assignments mirror ercot.com URL paths (e.g. `/committees/ros/dwg`);
> the authoritative list with chairs lives in `ERCOT_Stakeholder_Meetings_Links.md`.

### Sub-Tier Full Names

| Parent | Abbr | Full name |
|---|---|---|
| Board | F&A | Finance & Audit Committee |
| Board | HR&G | Human Resources & Governance Committee |
| Board | T&S | Technology & Security Committee |
| TAC | LLWG | Large Load Working Group |
| TAC | CFSG | Credit Finance Sub Group |
| TAC | RTCBTF | Real-Time Co-Optimization & Batteries Task Force *(winding down)* |
| ROS | BSWG | Black Start Working Group |
| ROS | DWG | Dynamics Working Group |
| ROS | IBRWG | Inverter-Based Resources Working Group |
| ROS | MWG | Meter Working Group |
| ROS | NDSWG | Network Data Support Working Group |
| ROS | OWG | Operations Working Group |
| ROS | OTWG | Operations Training Working Group |
| ROS | PDCWG | Performance, Disturbance & Compliance Working Group |
| ROS | PLWG | Planning Working Group |
| ROS | SPWG | System Protection Working Group |
| ROS | SSWG | Steady State Working Group |
| ROS | VPWG | Voltage Profile Working Group |
| RMS | TDTMS | Texas Data Transport & MarkeTrans Services Working Group |
| RMS | RMTTF | Retail Market Training Task Force |
| WMS | CMWG | Congestion Management Working Group |
| WMS | DSWG | Demand Side Working Group |
| WMS | SAWG | Supply Analysis Working Group |
| WMS | WMWG | Wholesale Market Working Group |

---

## Design System

Same CSS custom properties and Google Fonts as the main Power.Talks app. Must include `--bg-2` (`#EFEAE0` light / `#191816` dark) for the Board node background.

```css
:root {
  --bg:         #F6F3EE;
  --bg-2:       #EFEAE0;
  --panel:      #FBF9F5;
  --ink:        #1B1A17;
  --ink-2:      #3E3C37;
  --muted:      #86827A;
  --rule:       #E4DFD3;
  --rule-2:     #D8D2C3;
  --accent:     #C8623E;
  --accent-2:   #B0522F;
  --accent-soft:#F3E3D8;
  --sans:  'Inter Tight', ui-sans-serif, system-ui, sans-serif;
  --serif: 'Instrument Serif', Georgia, serif;
  --mono:  'JetBrains Mono', ui-monospace, monospace;
}
[data-theme="dark"] {
  --bg:         #121110;
  --bg-2:       #191816;
  --panel:      #1C1B19;
  --ink:        #F1EEE7;
  --ink-2:      #CDC9BF;
  --muted:      #8A857B;
  --rule:       #2A2824;
  --rule-2:     #35322D;
  --accent:     #E17A52;
  --accent-2:   #CC6A44;
  --accent-soft:#2A1E17;
}
```

---

## Page Header

Bolt SVG icon in a rounded terracotta square, serif title, muted subtitle — matches ERCOTHome and milestone page headers.

```html
<div class="hdr">
  <div class="hdr-logo">
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor"
         stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
      <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
    </svg>
  </div>
  <div>
    <div class="hdr-h1">ERCOT Stakeholder Process</div>
    <div class="hdr-sub">Organizational Chart — Revision Review Hierarchy</div>
  </div>
</div>
<hr class="hdr-rule"/>
<div class="sec-lbl">Committee &amp; governance hierarchy</div>
```

---

## Org Chart Layout Approach

Uses **explicit HTML elements** (not CSS pseudo-elements on `<ul>/<li>`) for predictable connector line rendering.

### Core elements

| Element | Purpose |
|---------|---------|
| `.org` | Flex column, `align-items: center` — vertical stack of all levels |
| `.vline` | `1px × 36px` vertical connector segment between nodes |
| `.tier` | `position: relative` full-width row centering a spine node — hosts a satellite |
| `.hline` | 30px horizontal connector from the spine node to its satellite (`left: calc(50% + 122px)`) |
| `.satellite` | Dashed card absolutely positioned at `left: calc(50% + 152px)`, vertically centered — Board committees / TAC WGs & TFs |
| `.hbranch` | Flex row for the multi-child level (4 subcommittees) |
| `.hbranch::before` | Horizontal bar spanning first-to-last child centers |
| `.hbranch-col` | `flex: 1` column inside branch — contains `.vline` + `.node` + `.vline` + `.wg-stack` |
| `.wg-stack` | Dashed card under each subcommittee listing its working groups (`.wg-stack--empty` variant for PRS) |
| `.wg-row` / `.wg-abbr` / `.wg-name` | One working-group line: mono abbr (min-width 52px) + small name |
| `.sat-eye` | Uppercase mono eyebrow label inside satellites and wg-stacks |

Page width is `max-width: 980px` (wider than other Power.Talks standalone
pages) so four subcommittee columns with stacks fit. The `@media (max-width:
760px)` block stacks everything vertically and hides connector lines.

### Horizontal bar calculation (4 equal children)

Each child column is `25%` of the total branch width. Their centers are at `12.5%`, `37.5%`, `62.5%`, `87.5%`. The horizontal bar spans from `left: 12.5%` to `right: 12.5%`:

```css
.hbranch::before {
  content: '';
  position: absolute;
  top: 0;
  left: 12.5%;
  right: 12.5%;
  height: 1px;
  background: var(--rule-2);
}
```

**If the number of children changes**, recalculate:
- `N` children → each column = `100%/N` → center of first = `100%/(2N)` → use that value for both `left` and `right`.

### HTML skeleton

```html
<div class="org">

  <div class="node node--puct">...</div>
  <div class="vline"></div>

  <div class="node node--board">...</div>
  <div class="vline"></div>

  <div class="node node--tac">...</div>
  <div class="vline"></div>

  <div class="hbranch">
    <div class="hbranch-col">
      <div class="vline"></div>
      <div class="node node--sub">...</div>
      <div class="vline"></div>
      <div class="wg-stack">
        <div class="sat-eye">Working Groups</div>
        <div class="wg-row"><span class="wg-abbr">DWG</span><span class="wg-name">Dynamics Working Group</span></div>
        <!-- one wg-row per working group / task force -->
      </div>
    </div>
    <!-- repeat for each subcommittee; PRS uses
         <div class="wg-stack wg-stack--empty">No standing working groups …</div> -->
  </div>

</div>
```

Board and TAC spine nodes are wrapped in a `.tier` with `.hline` +
`.satellite` for their sub-tiers:

```html
<div class="tier">
  <div class="node node--board">...</div>
  <div class="hline"></div>
  <div class="satellite">
    <div class="sat-eye">Board Committees</div>
    <div class="wg-row"><span class="wg-abbr">F&amp;A</span><span class="wg-name">Finance &amp; Audit Committee</span></div>
    ...
  </div>
</div>
```

---

## Node Styles

### CSS

```css
.node {
  border: 1px solid var(--rule-2);
  border-radius: 10px;
  background: var(--panel);
  padding: 13px 18px;
  text-align: center;
  position: relative; z-index: 1;
}
.node-abbr  { font-family: var(--mono); font-size: 12.5px; font-weight: 700; color: var(--accent-2); letter-spacing: .04em; margin-bottom: 4px; }
.node-name  { font-size: 11.5px; color: var(--ink-2); line-height: 1.45; }
.node-role  { font-family: var(--mono); font-size: 9px; text-transform: uppercase; letter-spacing: .08em; color: var(--muted); margin-top: 6px; }

/* PUCT — filled terracotta */
.node--puct { background: var(--accent); border-color: var(--accent-2); min-width: 230px; }
.node--puct .node-abbr { color: #fff; font-size: 14px; }
.node--puct .node-name { color: rgba(255,255,255,.82); }
.node--puct .node-role { color: rgba(255,255,255,.58); }

/* Board — muted bg */
.node--board { background: var(--bg-2); border-color: var(--rule-2); min-width: 230px; }

/* TAC — accent border */
.node--tac { border-color: var(--accent); border-width: 1.5px; min-width: 240px; }

/* Subcommittees — standard panel */
.node--sub { min-width: 118px; }
.node--sub .node-abbr { font-size: 12px; }
.node--sub .node-name { font-size: 10.5px; }
```

---

## Node Content

| Node | Abbr | Name | Role text |
|------|------|------|-----------|
| PUCT | `PUCT` | Public Utility Commission of Texas | Ultimate Regulatory Authority |
| Board | `Board of Directors` | ERCOT Board of Directors | Final Vote on Market Rule Changes |
| TAC | `TAC` | Technical Advisory Committee | Reviews Proposals & Recommends to Board |
| PRS | `PRS` | Protocol Revision Subcommittee | — |
| ROS | `ROS` | Reliability & Operations Subcommittee | — |
| RMS | `RMS` | Retail Market Subcommittee | — |
| WMS | `WMS` | Wholesale Market Subcommittee | — |

Subcommittee order on the branch row: **PRS, ROS, RMS, WMS** (left to right).
Sub-tier content (Board committees, TAC groups, working-group stacks) comes
from the **Sub-Tier Full Names** table above.

---

## Footer Note

Include a dashed-border note at the bottom explaining the revision request flow:

```html
<div class="note">
  <div class="note-eye">How revision requests flow</div>
  Revision requests — NPRRs, NOGRRs, PGRRs, RMGRRs, SCRs, COPMGRRs, and others — are
  submitted by market participants, ERCOT staff, or the PUCT to the relevant
  subcommittee: protocols to PRS, operating and planning guides to ROS, the retail
  market guide to RMS, and the commercial operations market guide to WMS. Working
  groups and task forces analyze issues and report to their parent subcommittee,
  which advances recommendations to TAC. TAC forwards approved revisions to the
  Board for a final vote, supported by its standing Board committees. The PUCT holds
  ultimate authority and may direct or override Board decisions on significant
  market design matters.
</div>
```

```css
.note {
  margin-top: 52px; padding: 14px 18px;
  border: 1px dashed var(--rule-2); border-radius: 10px;
  font-size: 11.5px; color: var(--ink-2); line-height: 1.7;
}
.note-eye {
  font-family: var(--mono); font-size: 9.5px; letter-spacing: .08em;
  text-transform: uppercase; color: var(--muted); font-weight: 500; margin-bottom: 5px;
}
```

---

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Horizontal bar doesn't reach all children | Recalculate `left`/`right` offsets: `100% / (2 × N children)` |
| `vline` inside `hbranch-col` misaligned | Ensure `.hbranch-col` has `align-items: center` |
| Board node too dark / invisible in dark mode | Use `var(--bg-2)` not `var(--ink)` for its background |
| `hbranch::before` missing `position: absolute` on parent | `.hbranch` must have `position: relative` |
| Forgetting `--bg-2` in dark mode overrides | Include `--bg-2: #191816` in `[data-theme="dark"]` block |
| Re-adding COPS as a subcommittee | COPS was absorbed into WMS — COPMGRRs are reviewed by WMS |
| Satellite overlaps the spine node | `.hline` starts at `calc(50% + 122px)` (half of the 230–240px node width); `.satellite` at `calc(50% + 152px)` — adjust both if node `min-width` changes |
| Working groups rendered as a horizontal branch row | ROS has 12 WGs — always render sub-tiers as vertical `.wg-stack` cards, never as another `.hbranch` |
| Page too narrow for 4 columns + stacks | `.page` uses `max-width: 980px` for this chart |
| Sub-tier list drifts from reality | Source of truth is the committee table in `ERCOT_Stakeholder_Meetings_Links.md` (URL paths give parentage) |
