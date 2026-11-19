---
name: GALLERY-Charts-Routine
description: Set up, run, tune and troubleshoot the Power.Talks GALLERY chart routine — a scheduled job, separate from the 1 AM daily refresh, that finds charts (timelines, flow charts, bar/line/area plots, org charts) inside ERCOT stakeholder PDFs, saves each one as Documents Database/GALLERY/GC_<timestamp>_<n>.png, and indexes it in the MySQL `gallery` schema as gallery_charts + gallery_keywords.
trigger: When the user asks to extract charts from meeting documents into the GALLERY, build or rebuild the gallery_charts / gallery_keywords tables, schedule or re-schedule the gallery chart routine, backfill the chart gallery, or debug why a chart was or was not picked up.
---

# GALLERY Charts Routine

Finds the charts buried in ERCOT stakeholder documents, saves each as a PNG in
the GALLERY, and indexes it so the web Gallery page can search on it.

It is **its own scheduled routine**, not a step of `run_routine.py`. Keep it
that way: it reads thousands of documents and it
spends an AI budget — any of which would push the 1 AM daily refresh past its
window or eat the quota the nightly summarizers depend on.

## Files

```
Database Codes/download_GALLERY_charts/
    gallery_charts_extractions_generations.py   the extractor (detect -> render -> index)
    gallery_db.py                               gallery schema: DDL, vocabulary, invariant
    run_gallery_routine.py                      the routine driver (keywords -> extract -> verify)
    run_gallery_routine.bat                     Task Scheduler wrapper
    register_gallery_task.ps1                   registers the separate Windows task
    GALLERY Charts Routine.md                   this file

Documents Database/GALLERY/
    GC_<YYYYMMDD_HHMMSS>_<n>.png                the extracted charts
    _extraction_state.json                      per-source-file state (incremental skip)
    routine_log/                                one log per run
```

## What a run does

1. **keywords** — `sync_keyword_ids.py` refreshes `gallery.keyword_id` from the
   curated `reference_info/ercot_keyword_vocabulary.yaml`, so the chart vocabulary
   is current before anything is matched against it.
2. **extract** — walks `Documents Database/ERCOT.STKHDR.MEETS/<GROUP>/<DATE>/`
   for **PDF** files that are new or changed, finds the chart
   pages, renders them, and upserts the two tables.
3. **verify** — re-asserts the keyword invariant (below) and repairs drift.

## Naming

`GC_<YYYYMMDD_HHMMSS>_<n>.png`, where the timestamp is taken **at the moment
the source file is opened** and `<n>` is the chart's sequence number within
that document. Every chart from one document therefore shares a timestamp, and
the file name alone tells you which pass produced it and in what order. The
PNG stem *is* the `chart_id`. A stamp already in use is nudged forward a second,
so a re-run never overwrites an earlier extraction.

## How a chart is recognised

Two stages, because neither works alone.

**1. Prefilter (deterministic, free).** For a PDF, per-page vector-stroke
counts are compared against *that document's median*. ERCOT decks draw the same
template furniture on every slide, so the raw count is mostly boilerplate and
only the **excess over the deck's own baseline** carries signal. A page becomes
a candidate on excess strokes, a dense cluster of numeric tokens (axis ticks and
data labels), or a large embedded picture.

Pictures get their own measurement, because a great many ERCOT charts are
pasted into the slide as an image and no text extraction can reach their axis
labels. The largest picture on the page is decoded and scored on two things: how
much of it is near-white (a chart sits on a white canvas; a photograph fills its
frame) and how many colours it uses after quantization (a chart uses a palette,
a photograph a continuum). On the calibration decks, charts-as-pictures measured
0.28–0.73 near-white with ≤84 colours, while photos, logos and UI screenshots
measured ≤0.16 with 6–263.

**2. Adjudication (AI, one call per document).** The candidate pages' titles,
text and measurements go to Claude in a **single call per document** — that is
what makes a multi-thousand-document backfill affordable. It returns which
pages really are charts, the chart type, the title, and the keywords.

### Workbooks are not a source (removed 2026-11-19)

Until 2026-11-19 the routine also exported chart objects out of .xlsx/.xls
through Excel COM. That path, and the 1,587 chart rows it had produced, were
removed; `remove_excel_charts.py` is the one-time migration that did it.

The reason was precision, not effort. A workbook chart gets no AI stage, so its
keywords could only come from a literal scan, and to find anything at all that
scan had to read the **series names** — at which point a series called
`Day-Ahead 1430 COP HSL` on a wind-forecast chart tagged it *Current Operating
Plan*. One such alias put a keyword on 522 charts, a third of the gallery, that
none of them was about. Workbook charts also arrive without the page context a
model needs to judge what a chart is for. A PDF page carries its own title,
caption and surrounding prose, so one call per document can decide what each
chart actually is.

With `--no-ai` the extractor keeps only its own high-confidence band. **Do not
use it to backfill PDFs.** Measured over the whole corpus on 2026-11-17, that
band keeps **13,323 of 51,168 pages — 26% of every page ERCOT has published**,
across 54% of all documents. It is not a conservative subset of the charts; it
is a quarter of the corpus. `--no-ai` is for debugging a single document and
only. A gallery built without the AI stage is not a smaller gallery, it is a
junk one.

Anything a `--no-ai` pass does write is provisional: the document is flagged so
a later AI-enabled run revisits it and replaces what it found (see *Incremental
behaviour*).

## The tables (`gallery` schema)

`gallery_charts` — one row per chart:
`chart_id` (= the PNG stem), `chart_title`, `doc_name`, `doc_type`
(`pdf`), `doc_group`, `doc_time`, `page_num` (the PDF page number),
`sequence_id`, `keywords`, `record_timestamp`.

`gallery_keywords` — one row per (keyword, chart):
`keyword_id`, `keyword`, `chart_id`, `record_timestamp`.

`doc_group` and `doc_time` are read from the source path
(`…/ERCOT.STKHDR.MEETS/<GROUP>/<YYYY-MM-DD>/<file>`).

### The keyword invariant

**`gallery_charts.keywords` may only contain values that exist as
`gallery_keywords.keyword` for that same chart.**

It holds by construction, not by hope: `write_chart()` takes one keyword list,
resolves it against `gallery.keyword_id`, writes `gallery_keywords` from the
resolved set, and serialises *that same set* into `gallery_charts.keywords`.
Anything the matcher cannot resolve is dropped, never invented — the AI's picks
are filtered through the vocabulary too, and a page whose picks all fail falls
back to a literal text scan. `verify_invariant()` then re-checks the whole table
and repairs drift, so the guarantee survives manual edits as well.

`keywords` is TEXT holding a JSON array rather than a native JSON column, so the
routine runs against whatever MySQL/MariaDB build WAMP ships. Read it with
`json.loads()`.

## Running it

```sh
# the routine, as the scheduler runs it
py -3 "Database Codes/download_GALLERY_charts/run_gallery_routine.py"

# pace a backfill: 600 documents and 150 AI calls a night
py -3 ".../run_gallery_routine.py" --max-docs 600 --ai-budget 150

# no AI at all (spends no quota)
py -3 ".../run_gallery_routine.py" --no-ai


# phase 3: a night of the PDF backfill
py -3 ".../run_gallery_routine.py" --max-docs 600 --ai-budget 650

# clean up after a night that was killed mid-document
py -3 ".../gallery_charts_extractions_generations.py" --prune

# see what would be extracted, writing nothing
py -3 ".../run_gallery_routine.py" --dry-run --group BOARD --since 2026-01-01
```

The extractor can also be driven on its own, which is what you want when
debugging one document:

```sh
py -3 ".../gallery_charts_extractions_generations.py" --dry-run --redo-file "13-CEO-Update.pdf"
py -3 ".../gallery_charts_extractions_generations.py" --verify-only
```

Exit codes: `0` fine, `1` something failed, `2` the AI subscription window was
used up — not an error, just a pause; the remaining documents are picked up by
the next run.

## Scheduling

```powershell
# elevated PowerShell
powershell -ExecutionPolicy Bypass -File ".\register_gallery_task.ps1"
powershell -ExecutionPolicy Bypass -File ".\register_gallery_task.ps1" -MaxDocs 600
powershell -ExecutionPolicy Bypass -File ".\register_gallery_task.ps1" -Unregister
```

Registers **"Power.Talks GALLERY Charts"**, daily at 04:30 — after the 1 AM
"Power.Talks Daily Refresh" has finished. Two details the script gets right and
a hand-made task usually does not:

* the path to the `.bat` is **quoted** (an unquoted path with a space in it has
  already cost this project a working scheduled task), and
* the principal is an **interactive** logon
  session and the AI backend needs the logged-in Claude subscription. A task set
  to "run whether user is logged on or not" has neither and will fail.

## Incremental behaviour

`_extraction_state.json` records each source file's size and mtime plus what was
extracted from it. A file whose size and mtime are unchanged is skipped without
being opened, so a nightly run only pays for documents that are new or that
ERCOT re-posted. `--rescan` re-reads everything; `--redo-file <substring>`
re-extracts one document. State is checkpointed every 20 documents, so a crash
mid-backfill keeps its progress.

**A re-extraction replaces, it does not accumulate.** `chart_id` carries the
timestamp of the pass that produced it, so a second pass over the same document
mints *new* ids and cannot overwrite the old rows by upsert. Before writing, the
extractor therefore retires the chart rows, keyword links and PNGs the previous
pass recorded in state. Without that step one re-run doubled a document's rows
(16 -> 18 in testing); with it, two consecutive re-runs leave the table
unchanged. This is what makes a backfill night safe to repeat.

**A `--no-ai` pass is provisional, and is upgraded later.** State records
`ai_pass` per document. A PDF last seen without adjudication is *not* treated as
finished: the next AI-enabled run revisits it, retires its provisional rows and
replaces them with adjudicated ones. So the cheap pass can never silently cap
the gallery's recall.

`--prune` drops chart rows and PNGs that the state no longer references — the
debris a night killed mid-document leaves behind. It is a maintenance command:
it writes nothing else and exits.

Documents are processed **newest meeting first**, so a paced backfill makes the
current material searchable before it works back through the archive.

## Backfill schedule

The corpus is **4,074 PDFs**, measured on 2026-11-17 (the 3,280 workbooks in
the tree are no longer a source). It cannot be done in one night, and the limit is the AI
subscription window, not CPU time. Measured rates:

| | measured |
|---|---|
| PDF prefilter (no AI) | 0.43 s/doc |
| PDF with adjudication | ~6.5 s/doc |
| PDFs producing >=1 candidate page | 86.3% -> **3,515 AI calls** (census, not sampled) |
| candidate pages per PDF | 8.0 mean, 4 median |
| candidate pages, whole corpus | 32,525 of 51,168 (64%) |
| AI prompt size | ~3,000 tokens mean, 13,400 max |

Phases, cheapest and least contended first:

1. **Census — no AI, writes nothing.** `--no-ai --dry-run --rescan`
   prefilters all 4,074 PDFs in ~35 min and reports exactly how many AI calls
   the next phase needs. **Done 2026-11-17: 3,515 calls.** Re-run it if the
   thresholds change, since it is the only way to price the AI phase before
   committing quota to it.
2. **Backfill — paced over about a week.** `--max-docs 600 --ai-budget 650`:
   roughly 65 min and ~520 AI calls a night, 4,074 PDFs in ~7 nights. This
   phase is not optional — see the `--no-ai` warning above. Newest meetings
   land first. If the subscription window runs out the run exits `2`, leaves
   the remaining documents unrecorded, and the next night resumes where it
   stopped — so the phase self-paces and overrunning the budget costs nothing
   but a day.
3. **Steady state.** Drop `--max-docs`; a nightly run then handles just the
   documents ERCOT posted that day.

Do not start phase 3 while another AI-heavy backfill is still running
nightly — the two will compete for the same subscription window and both will
stall. Check what else is scheduled first.

## AI cost

One call per document, on the **subscription** backend (`ai_backend.py`, `cli`
mode) — the project's standing rule is that no AI work goes to the metered API.
`--ai-budget` caps calls per run and `--max-docs` caps documents; the first
backfill over the full tree (~4,000 PDFs) should be paced across
several nights rather than attempted at once. If the subscription window runs
out mid-run the extractor stops making calls, leaves the remaining documents
**unrecorded** (so they are retried intact later) and exits `2`.

Override the model with `POWERTALKS_GALLERY_MODEL` (default `haiku`).

## Tuning and troubleshooting

All thresholds sit together at the top of
`gallery_charts_extractions_generations.py`:

| Knob | Meaning |
|---|---|
| `MIN_EXCESS_STROKES` | vector content a page needs beyond its deck's baseline |
| `MIN_NUMERIC_TOKENS` | numeric tokens that alone make a page a candidate |
| `MIN_IMAGE_AREA` | how much of the page a picture must cover to be measured |
| `IMG_WHITE_STRONG` / `IMG_WHITE_LIKELY` | near-white share for "this picture is a chart" |
| `IMG_MAX_COLORS` | palette size above which a picture reads as a photograph |
| `STRONG_*` | the `--no-ai` high-confidence band |
| `RENDER_DPI` | PDF page render resolution (150 ≈ the PNGs already in GALLERY) |

* **A chart was missed.** Run with `--dry-run --redo-file <name>` and read the
  per-page signals in the log. If the page never became a *candidate*, loosen a
  prefilter threshold. If it was a candidate the AI rejected, the page text and
  measurements were genuinely thin — usually a chart-as-picture on a dark
  background, which `IMG_WHITE_LIKELY` controls.
* **Junk was picked up.** Tighten `MIN_EXCESS_STROKES`, or check whether the
  deck has an unusually quiet template (a low baseline makes ordinary slides
  look busy).
* **No PNGs appear.** Confirm the task runs
  under an interactive logon. `~$`-prefixed lock files are skipped by design.
* **Keywords look wrong or empty.** The vocabulary is `gallery.keyword_id`;
  refresh it with `sync_keyword_ids.py` and re-run. Out-of-vocabulary
  suggestions are logged as dropped — they are not a bug, they are the
  invariant doing its job.
* **A keyword is attached to charts that have nothing to do with it.** Suspect
  a bad *surface form* rather than bad matching. `Vocabulary` registers the
  term, the term without its trailing parenthetical, the parenthetical itself,
  and each `/`- or `,`-separated token of the `acronym` column — so
  `Senate Bill 6 (SB6, 2025)` with acronym `"SB6, 2025"` once registered
  **`2025`**, and tagged every chart that merely mentioned the year (95 wrong
  links). Bare numbers are now rejected as aliases. To check a term's forms:
  `[k for k,(i,t) in vocab.by_key.items() if t == "<term>"]`.

### Re-running a subset

To re-extract specific documents without `--rescan` (which would re-read all
7,354), set `mtime` to `0` on their entries in `_extraction_state.json` and run
normally. Keep the entry itself — that is what the retire step reads to clean up
the previous rows and PNGs. Deleting the entry instead orphans them.

## Related

* `Database Codes/sync_keyword_ids.py` — owns `gallery.keyword_id`.
* `Database Codes/build_gallery_index.py` — maintains the *curated*
  `gallery_index.json` behind the web Gallery page and links its keywords to the
  glossary. Different artifact, same GALLERY folder: this routine populates
  MySQL, that one the hand-authored JSON.
* `Database Codes/run_routine.py` — the 1 AM daily refresh. Deliberately does
  **not** include this routine.
