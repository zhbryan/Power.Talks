---
name: Study-a-Topic
description: Use when asked to study, research, learn about, or be briefed on an ERCOT topic across the local knowledge base — "what's the history of co-located load", "brief me on RTC+B", "everything ERCOT has done about large flexible loads", "how did ECRS evolve". Drives the study index (Database Codes/study_index) to find the relevant issues, documents and meetings, then reads the real source documents and writes a dated study brief.
---

# Study a Topic

## Overview

Turns a topic question into a sourced study brief by searching the **derived**
knowledge layer (profiles, AI summaries, meeting profiles) to find out *where to
look*, then reading the **actual source documents** to find out *what is true*.

The index is a finding aid, not an authority. Every claim in a brief must trace
to a source document under `Documents Database/`, cited by issue ID and filename.

Two retrieval tiers, and the difference matters:

| Tier | Answers | Use it for |
|---|---|---|
| **Tier 1** — SQL over structured tables | exact, **complete** sets | "every NPRR touching Section 6.5", the full record for one issue |
| **Tier 2** — FTS5/BM25 over summaries | ranked, **partial** discovery | "what has ERCOT discussed about X" |

**Never state or imply completeness from a Tier 2 search.** A ranked search
returns the best matches, not all of them. Completeness claims come from Tier 1
only, and even then are bounded by the coverage limits listed below.

## Prerequisite — the index

```
py -3 "Database Codes/study_index/build_index.py"      # full rebuild, ~4s
py -3 "Database Codes/study_index/search.py" --stats    # coverage + built_at
```

The nightly routine rebuilds it as step 36 of 37. Before studying, check
`--stats` for two things:

- a `built_at` older than the newest profile, or a profiler running right now —
  rebuild, because a build taken mid-profiler captures a torn snapshot;
- a `warning` row. `source_documents` is added to each profile by
  `gen_mkt_doc_summaries.py` (routine step 25), *not* by the profilers, so an
  index built between those steps has **zero documents** and document-level
  search returns nothing. Issue and meeting search still work. Say so rather
  than reporting an empty document search as an absence of evidence.

All commands below run from the project root; `search.py` also runs from its own
folder. Add `--json` to any command for machine-readable output.

## Workflow

### 1. Fix the vocabulary first

ERCOT names the same thing several ways, and the right query is usually not the
user's phrasing.

```
py -3 "Database Codes/study_index/search.py" --terms "large flexible"
```

This reads the 791-term glossary + market-keyword vocabulary. `search.py`
expands acronyms automatically (`ECRS` also searches "ERCOT Contingency Reserve
Service", and the reverse), but check what the corpus actually calls the topic
before trusting a low match count. If the vocabulary is missing a synonym the
corpus uses, add it to `EXTRA_SYNONYMS` in `search.py` rather than working
around it in the query.

### 2. Discover — where is the topic discussed?

```
py -3 "Database Codes/study_index/search.py" "co-located load"
py -3 "Database Codes/study_index/search.py" "state of charge" --category NPRR --from 2024-01-01
py -3 "Database Codes/study_index/search.py" "ECRS" --what meetings --limit 25
```

Read the `matches:` line first — it reports total hits per table, independent of
`--limit`. If the totals are large, narrow with `--category` / `--from` / `--to`
/ `--committee` and raise `--limit`; if zero, re-check vocabulary, then try
`--strategy any`.

The `strategy` shown says how the query matched: `phrase` (exact phrases — most
trustworthy), `all` (every word, scattered), `any` (any word — treat the ranking
as weak and verify each hit).

### 3. Establish the complete set — only where it matters

If the brief will claim "all", "every", or a count, get it from Tier 1:

```
py -3 "Database Codes/study_index/search.py" --section 6.5          # includes subsections
py -3 "Database Codes/study_index/search.py" --section 2.1 --exact-section
py -3 "Database Codes/study_index/search.py" "firm fuel" --count
```

`--count` reports how many records match the full-text query — use it to say
"the index surfaces N issues", never "there are N issues".

### 4. Read the real documents

Discovery output gives each issue's `folder:` and each document's `file:`. Open
those documents — the PDFs, DOCs and DOCXs — for anything the brief asserts.

```
py -3 "Database Codes/study_index/search.py" --issue NPRR1348
```

That prints the issue's status, sponsor, sections, timeline and every source
document with its date and type. Then read the documents themselves from
`Documents Database/ERCOT.MKT.RULES/<CAT>/<ID>/`.

Order of authority, highest first:

1. The source document (revision request, comments, impact analysis, reports)
2. `Quick runs/<ID> Profile.json` — extracted metadata, deterministic
3. `Quick runs/<ID> Summary.json` — **AI-generated**; a lead, never a citation
4. Meeting `Quick runs/<CMTE>-<DATE> Profile.json` — AI-generated discussion notes

When a brief repeats something only an AI summary says, label it as such.

### 5. Build the chronology

A study brief's spine is the sequence. Combine:

- `--issue <ID>` timelines (normalised ISO dates, so they sort correctly)
- meeting dates from the discovery output, for when stakeholders debated it
- `date_posted` and `effective_date` for when a change was filed and took effect

Where the index date is `null`, the profile recorded something unparseable —
check `date_posted_raw` in the index or the document itself rather than guessing.

### 6. Write the brief

Save to `Documents Database/STUDY.TOPICS/<YYYY-MM-DD>-<slug>/`:

- `<slug> Study Brief.md` — the brief
- `_sources.json` — every issue ID, meeting and document file consulted, plus
  the exact search commands run, so the work is reproducible

Brief structure:

```markdown
# <Topic> — Study Brief
*Compiled <date> from the Power.Talks local knowledge base.*

## What it is
Plain-language definition, with the glossary/keyword term and acronym.

## Why it matters
The market problem driving it.

## Chronology
| Date | What happened | Where | Source |
Dated rows, earliest first; every row cites an issue ID or meeting.

## Current state
Status of the live revision requests, as of the index's built_at date.

## Open questions and disagreements
Who argued what — from comment documents and meeting debates, attributed.

## Coverage and limits
What was searched, what strategy matched, what this brief does NOT cover.

## Sources
Issue IDs, meeting dates, document filenames with paths.
```

## Coverage limits — state these honestly

The index covers the derived layer, and that layer is uneven:

- **1,712 market-rules issues** and **2,372 meetings** are indexed, against
  ~17,800 raw market-rules documents on disk. The index knows the per-document
  summaries the profiler wrote, **not** the full text of the PDFs.
- **1,568 of 1,712 issues** have at least one extracted section number; the rest
  recorded sections only as titles, so a `--section` query cannot see them.
- Meeting profiles are AI-written from meeting materials; several have empty
  `topics`/`agenda_items`, so a quiet meeting may be under-represented.
- Nothing from `ERCOT.PUBAPI`, `HOT.TOPICS` or `STATS.ILLUSTRATOR` is indexed —
  those are market data and daily reports, not rule or meeting knowledge.
- A topic that appears only inside a PDF body, and never in a title, summary or
  profile field, will not be found. Say so when a search comes back thin, rather
  than concluding the topic is absent.

## Command reference

| Need | Command |
|---|---|
| Coverage / freshness | `search.py --stats` |
| Vocabulary, acronyms | `search.py --terms "<text>"` |
| Topic discovery | `search.py "<topic>"` |
| One table only | `search.py "<topic>" --what issues\|documents\|meetings` |
| Filters | `--category NPRR --status Approved --committee ROS --from / --to` |
| Match totals only | `search.py "<topic>" --count` |
| Complete section set | `search.py --section 6.5 [--exact-section]` |
| Full issue record | `search.py --issue NPRR1348` |
| Machine-readable | add `--json` |
| Rebuild index | `build_index.py` |

## Worked example

> "What's the history of co-located load at ERCOT?"

```
search.py --terms "co-locat"                      # vocabulary + acronyms
search.py "co-located load"                       # 3 issues, 2 docs, 1 meeting
search.py "co-located load" --strategy any --limit 30   # widen: related framings
search.py --issue NPRR1329                        # full record + timeline
search.py --section 2.1                           # does it touch Definitions?
```

Then read `1329NPRR-01-Resource-Entity-Requirements-for-Self-Limiting-Facilities-041326.docx`
and the comment documents in that folder, and build the chronology from the
NPRR1329 / NPRR1348 / PGRR133 timelines plus the CMWG 2022-03-21 discussion.
The brief cites those documents; it does not cite the index.
