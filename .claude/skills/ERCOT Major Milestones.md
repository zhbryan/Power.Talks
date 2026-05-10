---
name: ERCOT Major Milestones
description: Generates or regenerates html/ERCOT Major Milestones.html — a standalone vertical timeline page listing ERCOT's key historical milestones, styled to match the Power.Talks design system.
trigger: When the user asks to generate, update, or rebuild the ERCOT milestones timeline page.
---

# ERCOT Major Milestones — Timeline Page Generator

## Overview

This skill writes `html/ERCOT Major Milestones.html` — a fully self-contained, standalone HTML file with no external JavaScript dependencies. It renders a vertical timeline with:

- **Left column** — year and optional month in monospace
- **Center gutter** — dot on a vertical connector line
- **Right column** — milestone title and a short paragraph description

Major milestones (Uri, legislative reform) are visually distinguished with a filled accent dot and a small tag chip above the title.

---

## Output File

```
html/ERCOT Major Milestones.html
```

This file is standalone — it loads only Google Fonts from an external source. It does NOT load React, Babel, or any bundled module.

---

## Design System

Use the same CSS custom properties as the main Power.Talks application:

```css
:root {
  --bg:         #F6F3EE;
  --panel:      #FBF9F5;
  --ink:        #1B1A17;
  --ink-2:      #3E3C37;
  --muted:      #86827A;
  --rule:       #E4DFD3;
  --rule-2:     #D8D2C3;
  --accent:     #C8623E;
  --accent-2:   #B0522F;
  --accent-soft:#F3E3D8;
  --sans:       'Inter Tight', ui-sans-serif, system-ui, sans-serif;
  --serif:      'Instrument Serif', Georgia, serif;
  --mono:       'JetBrains Mono', ui-monospace, monospace;
}
[data-theme="dark"] {
  --bg:         #121110;
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

**Font imports:**
```html
<link href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Inter+Tight:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
```

---

## Page Header

Matches the ERCOTHome header style — bolt SVG icon in a rounded terracotta square, serif title, muted subtitle.

```html
<div class="hdr">
  <div class="hdr-logo">
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor"
         stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
      <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
    </svg>
  </div>
  <div>
    <div class="hdr-h1">ERCOT Major Milestones</div>
    <div class="hdr-sub">Electric Reliability Council of Texas · Timeline</div>
  </div>
</div>
<hr class="hdr-rule"/>
<div class="sec-lbl">Key milestones since founding</div>
```

CSS:
```css
.page { max-width: 680px; margin: 0 auto; padding: 52px 32px 96px; }
.hdr { display: flex; align-items: center; gap: 14px; margin-bottom: 10px; }
.hdr-logo {
  width: 44px; height: 44px; border-radius: 11px;
  background: var(--accent); display: grid; place-items: center;
  flex-shrink: 0; color: #fff;
}
.hdr-h1 { font-family: var(--serif); font-size: 26px; font-weight: 700; color: var(--ink); margin: 0; line-height: 1.2; }
.hdr-sub { font-size: 12px; color: var(--muted); margin-top: 3px; }
.hdr-rule { border: none; border-top: 1px solid var(--rule); margin: 22px 0 34px; }
.sec-lbl {
  font-family: var(--mono); font-size: 10px; letter-spacing: .1em;
  text-transform: uppercase; color: var(--muted); font-weight: 500; margin-bottom: 32px;
}
```

---

## Timeline Structure

Each milestone is one `.tl-item` row containing three flex children: date, gutter (dot + connector line), content.

```html
<div class="tl">
  <div class="tl-item">                        <!-- add class="major" for landmark events -->
    <div class="tl-left">
      <span class="tl-year">YYYY</span>
      <span class="tl-month">Mon</span>         <!-- optional -->
    </div>
    <div class="tl-mid">
      <div class="tl-dot"></div>
      <div class="tl-line"></div>               <!-- omit on last item, or hide via CSS -->
    </div>
    <div class="tl-right">
      <div class="tl-tag">Tag Label</div>       <!-- optional, for major items only -->
      <div class="tl-title">Milestone Name</div>
      <p class="tl-desc">Short description.</p>
    </div>
  </div>
  <!-- ... more items -->
</div>
```

CSS:
```css
.tl-item { display: flex; align-items: stretch; }
.tl-left { width: 76px; flex-shrink: 0; align-self: flex-start; text-align: right; padding-top: 2px; }
.tl-year { display: block; font-family: var(--mono); font-size: 12px; font-weight: 700; color: var(--accent-2); line-height: 1.4; }
.tl-month { display: block; font-family: var(--mono); font-size: 9.5px; color: var(--muted); text-transform: uppercase; letter-spacing: .06em; line-height: 1.5; }
.tl-mid { width: 44px; flex-shrink: 0; display: flex; flex-direction: column; align-items: center; }
.tl-dot { width: 12px; height: 12px; border-radius: 50%; border: 2px solid var(--accent); background: var(--panel); flex-shrink: 0; margin-top: 4px; z-index: 1; }
.tl-item.major .tl-dot { background: var(--accent); }
.tl-line { flex: 1; width: 1px; background: var(--rule-2); margin-top: 5px; }
.tl-item:last-child .tl-line { display: none; }
.tl-right { flex: 1; padding-bottom: 38px; }
.tl-item:last-child .tl-right { padding-bottom: 0; }
.tl-tag {
  display: inline-block; font-family: var(--mono); font-size: 9.5px; font-weight: 600;
  letter-spacing: .07em; text-transform: uppercase;
  color: var(--accent-2); background: var(--accent-soft);
  padding: 2px 9px; border-radius: 99px; margin-bottom: 6px;
}
.tl-title { font-family: var(--serif); font-size: 16px; color: var(--ink); margin: 0 0 6px; line-height: 1.3; }
.tl-item.major .tl-title { font-size: 17px; }
.tl-desc { font-size: 12.5px; color: var(--ink-2); line-height: 1.72; margin: 0; }
```

---

## Milestones List

| Year | Month | Class | Tag | Title | Description |
|------|-------|-------|-----|-------|-------------|
| 1970 | — | — | — | ERCOT Council Founded | Established as a reliability council to coordinate the Texas interconnection following the 1965 Northeast blackout. ERCOT operates as an electrically isolated island largely separate from neighboring grids. |
| 1996 | — | — | — | Wholesale Market Opens | The PUC of Texas begins opening wholesale generation to competition in response to FERC Order 888, laying the groundwork for full retail deregulation. |
| 1999 | — | — | — | Senate Bill 7 — Electric Choice Act | Landmark legislation restructures the Texas electricity market, mandating full retail competition starting January 2002 and formally establishing ERCOT as the independent system operator. |
| 2002 | Jan | — | — | Retail Competition Begins | Texas launches full retail electric choice across most of the ERCOT footprint, giving roughly 85% of customers the ability to choose their own retail electric provider (REP). |
| 2003 | — | — | — | Nodal Market Design Adopted | ERCOT's board selects a nodal market design over the existing zonal model to improve locational price signals and reduce transmission congestion costs. |
| 2007 | — | — | — | CREZ Transmission Authorized | The PUC approves the Competitive Renewable Energy Zones (CREZ) initiative — approximately 3,600 miles of new high-voltage lines to connect West Texas wind to load centers. |
| 2010 | Dec | — | — | Nodal Market Goes Live | ERCOT transitions from zonal to nodal market operations, implementing locational marginal pricing (LMP) at over 8,500 settlement points. |
| 2013 | — | — | — | CREZ Transmission Complete | The final CREZ lines are energized, unlocking over 11,000 MW of previously constrained wind generation in West Texas. |
| 2014 | Jun | — | — | ORDC Adopted | ERCOT implements the Operating Reserve Demand Curve (ORDC), adding a real-time scarcity adder to energy prices when operating reserves fall below defined thresholds. Prices reliability directly into the market and reduces reliance on manual emergency interventions. |
| 2019 | — | — | — | 100 GW Generation Milestone | ERCOT's total installed generation capacity surpasses 100,000 MW for the first time, driven by growth in wind, solar, and gas resources. |
| 2021 | Feb | major | Historic Event | Winter Storm Uri | A catastrophic winter storm causes the largest grid failure in ERCOT's history. Nearly 10 million Texans lose power; ~246 die; economic losses exceed $195B. Triggers sweeping market and governance reform. |
| 2021 | Jun | major | Legislative Reform | SB 2 & SB 3 Enacted | SB 3 mandates winterization of power plants and fuel infrastructure; SB 2 overhauls ERCOT governance, replacing the industry-majority board with independent directors. |
| 2022 | — | — | — | Capacity Market Proposal Rejected | The PUC rejects the Performance Credit Mechanism (PCM) capacity market proposal, choosing targeted enhancements to the energy-only market design instead. |
| 2023 | Aug | — | — | All-Time Demand Record | ERCOT sets an all-time peak demand record of 85,508 MW during an extreme heat wave, with the grid holding without emergency conditions. |
| 2024 | — | — | — | Large Load Demand Surge | ERCOT's interconnection queue is overwhelmed by unprecedented requests from cryptocurrency miners, AI data centers, and industrial users, prompting new large flexible load policies from ERCOT and the PUC. |
| 2025 | — | major | Legislative Reform | SB 6 — Large Load Framework | The 89th Texas Legislature establishes a regulatory framework requiring large flexible loads (crypto miners, AI data centers, high-consumption industrial users) to register with ERCOT, demonstrate curtailability, and meet new interconnection standards. |
| 2025 | Dec | — | — | RTC-B Goes Live | Real-Time Co-optimization with Batteries launches, simultaneously optimizing energy and ancillary service awards for battery storage in the real-time market — a landmark step in storage integration. |

---

## Implementation Steps

1. Write the complete HTML to `html/ERCOT Major Milestones.html` using the structure above.
2. Include the full CSS (design tokens + dark mode + layout + timeline classes) in a single `<style>` block in `<head>`.
3. No JavaScript required — pure HTML/CSS only.
4. Verify at `http://localhost/Power.Talks/html/ERCOT%20Major%20Milestones.html`.

---

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Missing `align-self: flex-start` on `.tl-left` | Without it, `.tl-left` stretches full height and date appears top-left instead of aligned to dot |
| Connector line on last item | Hide with `.tl-item:last-child .tl-line { display: none; }` |
| Using `align-items: flex-start` on `.tl-item` | Use `stretch` so `.tl-mid` fills the row height and the connector line reaches the next item |
| Forgetting dark mode token block | Always include `[data-theme="dark"]` overrides |
