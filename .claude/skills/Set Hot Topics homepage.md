---
name: Set-Hot-Topics-Homepage
description: Skill for building and maintaining the "Hot Topics" section homepage on the Power.Talks website — the center view that shows the daily ERCOT Hot Topics reports with a date dropdown (defaulting to the most recent), rendering content live from the Markdown reports under Documents Database/HOT.TOPICS/. Covers the HotTopicsHome component, the in-browser Markdown renderer, the index.json data feed, and the rebuild workflow.
trigger: When the user asks to create, change, or debug the Hot Topics section/homepage on the website, its date dropdown, or how the daily Hot Topics reports are displayed on the page.
---

# Set Hot Topics Homepage

## What this is

The **Hot Topics** section (`activeSection === "hot-topics"`) renders the daily
ERCOT market-intelligence reports produced by the **Hot Topics Generator** skill.
The center view is the `HotTopicsHome` React component with:

- a **date dropdown** (top-right) listing every available report date, newest
  first;
- the **most recent date selected by default**;
- the selected day's report **fetched live from WAMP and rendered from Markdown
  in the browser** — so a new daily report shows up **without rebuilding the
  bundle**; only `index.json` needs refreshing.

Read the **Set-Power-Talks-Website-Framework** skill first for the app shell,
the JSX-bundle pipeline, and the module contract. This skill covers only the
Hot Topics section.

## Data flow

```
Documents Database/HOT.TOPICS/
    index.json                         ← list of dates (dropdown feed)
    <YYYY-MM-DD>/
        hot_topics_<YYYY-MM-DD>.md     ← the report the page renders
```

- **`index.json`** — `{ "generated_at", "dates": [ {date, file, title}, … ] }`,
  **newest first**. Written by
  `Database Codes/hot_topics/gen_hot_topics.py` (every run, and standalone via
  `--index-only`). The page reads `dates[0]` as the default selection.
- **Report Markdown** — the same file the generator writes. The page fetches it
  as text and renders it; nothing is pre-converted to HTML.

Both are served over WAMP under the `/Power.Talks` prefix, matching the site's
other live-data pattern:

| Fetch | URL |
|---|---|
| Date list | `/Power.Talks/Documents%20Database/HOT.TOPICS/index.json` |
| A report  | `/Power.Talks/Documents%20Database/HOT.TOPICS/<date>/hot_topics_<date>.md` |

## Where the code lives

| Piece | Location |
|---|---|
| `HotTopicsHome` component + Markdown renderer | `html/src/illustration.jsx` (appended after `ERCOTHome`; exports `window.HotTopicsHome`) |
| Section route | `html/src/app.jsx` — `activeSection === "hot-topics" ? <HotTopicsHome/> : …` in the `MessageStream` illustration switch |
| Sidebar / quick-access entry | already present: `sidebar.jsx` and `ERCOTHome`'s LINKS both use `{ id: "hot-topics", icon: "Flame" }` |
| Date-list feed | `Database Codes/hot_topics/gen_hot_topics.py` → `write_index()` |

The component was placed **inside `illustration.jsx`** on purpose:
`rebuild_standalone.py` only *updates* existing bundle entries (it can't add a
new module), so reusing an existing module keeps the rebuild at **11 entries**.
Don't split it into a new `src/*.jsx` file unless you also hand-add a manifest
entry + an `ANCHORS` row.

## The in-browser Markdown renderer

`htMarkdownToHtml(md)` (with helpers `htEscape`, `htInline`, `htParseList`)
converts the report Markdown to HTML for `dangerouslySetInnerHTML`. It is
deliberately scoped to the constructs the daily reports use:

- `#`/`##`/`###…` headings — **the first `# H1` is dropped** (the date already
  shows in the header + dropdown);
- **GFM tables** with `:---`/`:--:`/`---:` alignment (the topic-ranking table);
- bullet lists with **one level of nesting** (2-space indent);
- `**bold**`, `*italic*`, `` `code` ``, `[text](url)` links (open in a new tab);
- `>` blockquotes and `---` horizontal rules; blank-line-separated paragraphs.

Content is **HTML-escaped first**, so Markdown source can't inject raw markup.
If a future report introduces a new construct (images, ordered lists, nested
tables), extend the renderer — don't add a CDN Markdown library (the framework
pins its CDN scripts and loads no bundler).

Styling is a scoped `<style>` block using `.ht-*` classes and the site's CSS
vars (`--ink`, `--panel`, `--accent`, `--mono`, `--serif`, …), so it themes with
light/dark like the rest of the app. Wide tables scroll inside their own
`overflow-x` container.

### Website shows only the ranking, not the raw sources

The page renders **only the top of each report** — the title/scope line, the
**🔥 Top Hot Topics** ranking table, and the "Hottest theme" narrative. The
**📋 Source Summaries** and **🗂️ Sources checked** sections are **hidden on the
website but kept in full in the database `.md` files** (they're the audit trail).

This is done at render time by `htStripSections(md, HT_HIDDEN_SECTIONS)` before
`htMarkdownToHtml` — it drops any `##` section whose heading matches
`HT_HIDDEN_SECTIONS` (`["Source Summaries", "Sources checked"]`, emoji/
punctuation ignored) together with its `###` subsections, resuming at the next
non-hidden heading. To show/hide a different section, edit that array — **don't**
change the generated report, which must retain everything for the record.

## Component states

`HotTopicsHome` handles: `loading` / `error` (index fetch failed — usually WAMP
not serving) / `empty` (no reports yet) for the index, and
`loading` / `error` / `ready` for the selected report. Fetches use
`cache: "no-store"` so a freshly regenerated report shows on refresh.

## Workflows

### Add a new day's report to the site
1. Generate the report (Hot Topics Generator skill) — it lands under
   `Documents Database/HOT.TOPICS/<date>/`.
2. Refresh the dropdown feed:
   ```bash
   py -3 "Database Codes/hot_topics/gen_hot_topics.py" --index-only
   ```
   (A full `gen_hot_topics.py` run also rewrites `index.json`.)
3. Hard-refresh the page — **no rebuild needed**. The new date appears at the
   top of the dropdown and is selected by default.

### Change the component (layout, renderer, styling)
1. Edit `html/src/illustration.jsx` (and `app.jsx` if touching the route).
2. `py -3 "html/rebuild_standalone.py"` → must report **11 entries** (incl.
   `illustration.jsx`, `app.jsx`).
3. Hard-refresh `http://localhost/Power.Talks/html/Power.Talks%20home%20page.html`
   (Ctrl+F5) and verify by driving the real page — open the section from the
   sidebar (**Hot Topics**, flame icon) or the ERCOT-home Quick-Access grid.

## Verifying

- `index.json`, the report `.md`, and the home page each return **200** over
  `http://localhost/Power.Talks/…`.
- The served bundle contains the component: decode the `illustration.jsx`
  manifest entry and grep for `function HotTopicsHome` / `window.HotTopicsHome`
  and the `app.jsx` entry for `<HotTopicsHome/>`.
- Renderer sanity: the topic-ranking table becomes a `<table class="ht-table">`
  with a header row + one row per topic; `**bold**` → `<strong>`; `&` → `&amp;`.

## Common mistakes

| Mistake | Fix |
|---|---|
| New report doesn't appear in the dropdown | Run `gen_hot_topics.py --index-only` — the page reads `index.json`, not the folder |
| Edited the component but page unchanged | The served page is a frozen bundle — run `rebuild_standalone.py`, then Ctrl+F5 |
| Split the component into a new `src/*.jsx` | `rebuild_standalone.py` only updates the 11 known entries; keep it in `illustration.jsx` or hand-add a manifest + anchor |
| Dropdown empty / "Couldn't load the index" | WAMP not serving, or `index.json` missing — check the HTTP 200s and regenerate the index |
| Bare `/Documents Database/…` fetch path | Must carry the `/Power.Talks` prefix and `%20` for the space, or it 404s |
| A new Markdown construct renders as raw text | Extend `htMarkdownToHtml` — do not add a CDN Markdown lib |

## Related skills

- **Hot Topics Generator** — produces the reports + `index.json` this page reads.
- **Set-Power-Talks-Website-Framework** — the app shell, bundle pipeline, module
  contract, and rebuild workflow.
- **Set-ERCOT-Homepage** — the `market-home` landing view whose Quick-Access
  grid links into this section.
