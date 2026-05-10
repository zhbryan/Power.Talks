---
name: ERCOT Introduction
description: Generates or regenerates the ERCOTHome component in illustration.jsx — replaces the live grid statistics and GRID NORMAL badge with two static introduction sections (ERCOT ISO overview and market rules / stakeholder process), while keeping the Quick Access links. Also patches the standalone bundle.
trigger: When the user asks to generate, update, or rebuild the ERCOT home page or ERCOT introduction content.
---

# ERCOT Introduction — Home Page Generator

## Overview

This skill rewrites the `ERCOTHome` function in `html/src/illustration.jsx`.

**Remove:**
- The `GRID NORMAL` badge from the header (`pt-ercot-badge`)
- The live-statistics grid (`STATS` array + `.pt-ercot-stats` block)
- The horizontal rule (`pt-ercot-rule`) between stats and Quick Access

**Keep:**
- The header row: bolt icon + ERCOT title + subtitle
- The Quick Access section: `pt-ercot-qlbl` label + `pt-ercot-links` grid

**Add (between header and Quick Access):**
- Two introduction text blocks with a divider between them:
  1. ERCOT ISO and the Wholesale Electricity Market
  2. Market Rules and the Stakeholder Process

---

## Target File

```
html/src/illustration.jsx
```

The `ERCOTHome` function starts with the comment:
```js
// ERCOT market home page — shown when ERCOT is selected from the ISO market list
```

---

## Introduction Content

### Block 1 — ERCOT ISO and the Wholesale Electricity Market

**Eyebrow label:** `About ERCOT`

**Body text:**
> ERCOT (Electric Reliability Council of Texas) is the independent system operator (ISO) for roughly 90% of Texas's electric load, managing over 89,000 MW of generation capacity and serving approximately 26 million customers. As a non-profit, member-governed organization, ERCOT operates one of the largest competitive wholesale electricity markets in North America. The market is energy-only — there is no separate capacity market — relying instead on real-time scarcity pricing and ancillary service markets to maintain grid reliability and incentivize investment in generation resources. ERCOT is unique among U.S. ISOs in operating an intrastate grid largely isolated from neighboring interconnections, giving Texas significant autonomy over its own market design. Most recently, ERCOT launched Real-Time Co-optimization with Batteries (RTC-B), a landmark market enhancement that simultaneously optimizes energy and ancillary service awards for battery storage resources in the real-time market — enabling batteries to provide multiple grid services at once and significantly improving the efficiency of storage dispatch across the grid.

---

### Block 2 — Market Rules and the Stakeholder Process

**Eyebrow label:** `Market Rules & Stakeholder Process`

**Body text:**
> ERCOT's market rules are codified in the Nodal Protocols and several associated guides — the Planning Guide, Operating Guide, Retail Market Guide, Verifiable Cost Manual, and others. Changes to these rules are proposed through standardized revision requests submitted by any market participant, ERCOT staff, or the Public Utility Commission of Texas (PUCT): NPRRs (Nodal Protocol), NOGRRs (Operating Guide), PGRRs (Planning Guide), COPMGRRs (Commercial Operations), and more. Each request advances through a structured stakeholder review: working groups and subcommittees — WMS, COPS, RMS, PRS — analyze and discuss the proposal, which then proceeds to the Technical Advisory Committee (TAC) for recommendation. TAC sends approved revisions to the ERCOT Board of Directors for final vote. The PUCT holds ultimate regulatory authority and may direct or override Board decisions on significant market design matters.

---

## CSS Classes to Add

Add these inside the `<style>` block of `ERCOTHome`, alongside the existing classes:

```css
.pt-ercot-intro { margin-bottom: 20px; }
.pt-ercot-intro-eye {
  font-family: var(--mono); font-size: 10px; letter-spacing: .1em;
  text-transform: uppercase; color: var(--muted); font-weight: 500;
  margin-bottom: 7px;
}
.pt-ercot-intro-body {
  font-size: 13px; color: var(--ink-2); line-height: 1.75;
}
.pt-ercot-intro-divider {
  border: none; border-top: 1px dashed var(--rule-2); margin: 18px 0;
}
```

**Remove these CSS classes** (they are no longer used):
- `.pt-ercot-badge` and its rules
- `.pt-ercot-stats`, `@media` rule for it
- `.pt-ercot-stat`
- `.pt-ercot-stat-val` and `.pt-ercot-stat-val .u`
- `.pt-ercot-stat.ok .pt-ercot-stat-val`
- `.pt-ercot-stat-lbl`
- `.pt-ercot-rule`

---

## New ERCOTHome JSX Structure

Replace the entire `ERCOTHome` function with the following. Preserve the leading comment and `window.ERCOTHome = ERCOTHome;` export.

```jsx
// ERCOT market home page — shown when ERCOT is selected from the ISO market list
function ERCOTHome({ onSectionChange }) {
  const LINKS = [
    { id: "paper-trails",     icon: "Book",      label: "Paper Trails",     desc: "NPRRs, NOGRRs, COPMGRRs and more"  },
    { id: "meeting-tracks",   icon: "Waveform",  label: "Meeting Tracks",   desc: "TAC, COPS, RMS committee activity"  },
    { id: "hot-topics",       icon: "Flame",     label: "Hot Topics",       desc: "Market design issues and debates"   },
    { id: "daily-headlines",  icon: "Lightning", label: "Daily Headlines",  desc: "Latest ERCOT news and alerts"       },
    { id: "stats-illustrated",icon: "Chart",     label: "Stats Illustrator",desc: "Charts, data, and market analytics" },
    { id: "gallery",          icon: "Folder",    label: "Gallery",          desc: "Documents, filings, and archives"   },
  ];
  return (
    <div className="pt-ercot-home">
      <style>{`
        .pt-ercot-home { padding: 24px 28px 32px; max-width: 760px; margin: 0 auto; }
        .pt-ercot-hdr {
          display: flex; align-items: center; gap: 14px; margin-bottom: 22px;
        }
        .pt-ercot-logo {
          width: 48px; height: 48px; border-radius: 12px;
          background: var(--accent); display: grid; place-items: center;
          flex: 0 0 auto; color: #fff;
        }
        .pt-ercot-h1 {
          font-family: var(--serif); font-size: 32px; font-weight: 700;
          color: var(--ink); margin: 0; line-height: 1.15;
        }
        .pt-ercot-sub { color: var(--ink-2); font-size: 13px; margin-top: 2px; }
        .pt-ercot-intro { margin-bottom: 20px; }
        .pt-ercot-intro-eye {
          font-family: var(--mono); font-size: 10px; letter-spacing: .1em;
          text-transform: uppercase; color: var(--muted); font-weight: 500;
          margin-bottom: 7px;
        }
        .pt-ercot-intro-body {
          font-size: 13px; color: var(--ink-2); line-height: 1.75;
        }
        .pt-ercot-intro-divider {
          border: none; border-top: 1px dashed var(--rule-2); margin: 18px 0;
        }
        .pt-ercot-qlbl {
          font-size: 11px; font-family: var(--mono); letter-spacing: .08em;
          text-transform: uppercase; color: var(--muted); font-weight: 500; margin-bottom: 10px;
        }
        .pt-ercot-links {
          display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px;
        }
        @media (max-width: 560px) { .pt-ercot-links { grid-template-columns: 1fr; } }
        .pt-ercot-lnk {
          display: flex; align-items: flex-start; gap: 12px;
          padding: 14px 16px; border: 1px solid var(--rule-2);
          border-radius: 10px; background: var(--panel);
          color: var(--ink); text-align: left; cursor: pointer;
          transition: border-color .15s, transform .1s, box-shadow .1s;
        }
        .pt-ercot-lnk:hover {
          border-color: var(--accent); transform: translateY(-1px); box-shadow: var(--shadow-1);
        }
        .pt-ercot-lnk-ico {
          width: 32px; height: 32px; border-radius: 8px;
          background: var(--accent-soft); display: grid; place-items: center;
          color: var(--accent-2); flex: 0 0 auto;
        }
        .pt-ercot-lnk b { display: block; font-weight: 500; font-size: 13.5px; margin-bottom: 2px; }
        .pt-ercot-lnk span { font-size: 12px; color: var(--muted); line-height: 1.4; }
      `}</style>

      <div className="pt-ercot-hdr">
        <div className="pt-ercot-logo"><I.Bolt size={22}/></div>
        <div>
          <h1 className="pt-ercot-h1">ERCOT</h1>
          <div className="pt-ercot-sub">Electric Reliability Council of Texas</div>
        </div>
      </div>

      <div className="pt-ercot-intro">
        <div className="pt-ercot-intro-eye">About ERCOT</div>
        <div className="pt-ercot-intro-body">
          ERCOT (Electric Reliability Council of Texas) is the independent system operator (ISO) for roughly 90% of Texas's electric load, managing over 89,000 MW of generation capacity and serving approximately 26 million customers. As a non-profit, member-governed organization, ERCOT operates one of the largest competitive wholesale electricity markets in North America. The market is energy-only — there is no separate capacity market — relying instead on real-time scarcity pricing and ancillary service markets to maintain grid reliability and incentivize investment in generation resources. ERCOT is unique among U.S. ISOs in operating an intrastate grid largely isolated from neighboring interconnections, giving Texas significant autonomy over its own market design. Most recently, ERCOT launched Real-Time Co-optimization with Batteries (RTC-B), a landmark market enhancement that simultaneously optimizes energy and ancillary service awards for battery storage resources in the real-time market — enabling batteries to provide multiple grid services at once and significantly improving the efficiency of storage dispatch across the grid.
        </div>
      </div>

      <hr className="pt-ercot-intro-divider"/>

      <div className="pt-ercot-intro">
        <div className="pt-ercot-intro-eye">Market Rules &amp; Stakeholder Process</div>
        <div className="pt-ercot-intro-body">
          ERCOT's market rules are codified in the Nodal Protocols and several associated guides — the Planning Guide, Operating Guide, Retail Market Guide, Verifiable Cost Manual, and others. Changes to these rules are proposed through standardized revision requests submitted by any market participant, ERCOT staff, or the Public Utility Commission of Texas (PUCT): NPRRs (Nodal Protocol), NOGRRs (Operating Guide), PGRRs (Planning Guide), COPMGRRs (Commercial Operations), and more. Each request advances through a structured stakeholder review — working groups and subcommittees (WMS, COPS, RMS, PRS) analyze and discuss the proposal, which then proceeds to the Technical Advisory Committee (TAC) for recommendation. TAC sends approved revisions to the ERCOT Board of Directors for final vote. The PUCT holds ultimate regulatory authority and may direct or override Board decisions on significant market design matters.
        </div>
      </div>

      <hr className="pt-ercot-intro-divider"/>

      <div className="pt-ercot-qlbl">Quick Access</div>
      <div className="pt-ercot-links">
        {LINKS.map(l => {
          const Ico = I[l.icon];
          return (
            <button key={l.id} className="pt-ercot-lnk" onClick={() => onSectionChange && onSectionChange(l.id)}>
              <div className="pt-ercot-lnk-ico"><Ico size={16}/></div>
              <div><b>{l.label}</b><span>{l.desc}</span></div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

window.ERCOTHome = ERCOTHome;
```

---

## Quick Runs Panel — ERCOT Home Page Context

When the active section is `"market-home"` (ERCOT home page), `RightPanel` in `html/src/rightpanel.jsx` shows only the **Artifacts tab** — the "For the talk" tab is hidden entirely. The Artifacts tab contains two ERCOT-specific entries defined in a module-level constant above `RightPanel`:

### Artifacts tab — two buttons

```js
const ERCOT_HOME_ARTIFACTS = [
  {
    id: "ercot-a1",
    title: "ERCOT major milestones timeline",
    desc: "Generate a historical timeline of ERCOT's major milestones since its founding — from deregulation and market launch through nodal transition, Winter Storm Uri, and the RTC-B era.",
    icon: "Chart",
    tag: "History"
  },
  {
    id: "ercot-a2",
    title: "ERCOT stakeholder process org chart",
    desc: "Show the current ERCOT stakeholder process organization chart — working groups, subcommittees, TAC, and Board.",
    icon: "Chart",
    tag: "Visual"
  },
];
```

### Wiring in RightPanel

Inside `RightPanel`, after extracting context flags:

```js
const isErcotHome = ctx.section === "market-home";
const activeArtifacts = isErcotHome ? ERCOT_HOME_ARTIFACTS : (ARTIFACTS || []);
```

Auto-switch to the artifacts tab whenever ERCOT home becomes active:

```js
React.useEffect(() => { if (isErcotHome) setTab("artifacts"); }, [isErcotHome]);
```

Hide the "For the talk" tab button and its content entirely when on ERCOT home:

```jsx
{/* Tab button — hidden on ERCOT home */}
{!isErcotHome && <button ...>For the talk</button>}

{/* Tab content — gated */}
{tab === "runs" && !isErcotHome && (...)}
```

Replace `ARTIFACTS` → `activeArtifacts` in the artifacts render. `SUGGESTED_RUNS` / `ERCOT_HOME_RUNS` are not used on the ERCOT home page at all.

**Note:** The rightpanel UUID in the bundle must also be patched — find it by searching for `window.RightPanel` in the decompressed bundle entries.

---

## Implementation Steps

1. **Edit `html/src/illustration.jsx`**
   - Locate the `ERCOTHome` function (search for `// ERCOT market home page`).
   - Replace everything from that comment through `window.ERCOTHome = ERCOTHome;` with the JSX block above.

2. **Patch both bundle files** — `html/Power.Talks home page.html` and `html/Power.Talks home page.html.bak`
   - The illustration bundle UUID is `ddaf2233-7d40-41f0-acf6-d688902f79d7`.
   - Use PowerShell with `System.IO.Compression.GZipStream` to:
     1. Read the file with `[System.IO.File]::ReadAllText` (UTF-8).
     2. Locate the UUID entry in the `__bundler/manifest` JSON using a regex on the one large manifest line.
     3. Read the updated `illustration.jsx`, compress it (GZip → Base64).
     4. Replace the old `"data":"..."` value for that UUID with the new Base64 string.
     5. Write back with `[System.IO.File]::WriteAllText` (UTF-8).
   - Repeat for the `.bak` file — it shares the same UUID.

3. **Verify** by opening `http://localhost/Power.Talks/html/Power.Talks%20home%20page.html` and confirming the ERCOT home page shows both introduction paragraphs (with RTC-B content), six Quick Access buttons, and no statistics or GRID NORMAL badge.

---

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Leaving the `STATS` array in the function | Remove it entirely — the new function has no `STATS` |
| Forgetting to remove `pt-ercot-badge` CSS | Delete the entire `.pt-ercot-badge` rule block from `<style>` |
| Not patching the standalone bundle | Always patch `Power.Talks home page.html` after editing the JSX source |
| HTML entities in JSX | Use `&amp;` for `&` inside JSX text nodes (e.g. `Market Rules &amp; Stakeholder Process`) |
