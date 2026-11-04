# study_index — tiered retrieval over the local knowledge base

A SQLite + FTS5 index over the **derived** knowledge layer the nightly routine
already produces, built to answer topic questions across the whole corpus
without embedding 22 GB of source documents.

| | |
|---|---|
| Indexed | 1,712 market-rules issues, 15,216 per-document write-ups, 2,372 meetings, 791 vocabulary terms |
| Index size | ~40 MB |
| Full rebuild | ~4 seconds |
| Source corpus it points into | ~22 GB, ~63,000 files |

## Why this shape

The knowledge base already had a strong answer for *procedural* questions —
29 skills that know exactly where an issue lives and what to extract. What it
lacked was **discovery**: given a topic, which of 23,651 market-rules files are
relevant? `grep` only finds literal strings, so "co-located load" misses the
revision request that says "co-location".

Classic vector RAG over the raw PDFs would fix discovery but cost a lot and
damage what already worked: embeddings blur near-identical identifiers
(NPRR1176 vs NPRR1167), chunking destroys the status/timeline structure the
profilers carefully extract, and top-k retrieval cannot answer "every NPRR
touching Section 6.5" — a completeness question that matters for regulatory work.

So the index covers the derived layer instead, in two tiers:

- **Tier 1 — structured SQL.** Exact and *complete*: issues, sections,
  timelines, documents, meetings, vocabulary. 1,900 distinct section numbers are
  extracted out of the free-text section strings so subtree queries work.
- **Tier 2 — FTS5 / BM25 full text.** Ranked discovery over titles, executive
  summaries, backgrounds, key changes, stakeholder debates, ERCOT/IMM opinions
  and every per-document summary, with acronym and synonym expansion driven by
  the ERCOT glossary and market-keyword list.

Embeddings remain a deliberate Tier 3 that has **not** been built. If BM25 plus
vocabulary expansion proves insufficient, embed the ~3,400 summaries — not the
17,833 PDFs.

## Files

| File | Purpose |
|---|---|
| `build_index.py` | Full rebuild into `study_index.db` (atomic: builds a `.tmp`, then replaces) |
| `search.py` | Query CLI — discovery, completeness, issue records, vocabulary |
| `study_index.db` | Generated; git-ignored |

## Usage

```bash
# build
py -3 "Database Codes/study_index/build_index.py"

# discovery (Tier 2)
py -3 "Database Codes/study_index/search.py" "co-located load"
py -3 "Database Codes/study_index/search.py" "state of charge" --category NPRR --from 2024-01-01
py -3 "Database Codes/study_index/search.py" "ECRS" --what meetings --limit 25

# completeness / exact (Tier 1)
py -3 "Database Codes/study_index/search.py" --section 6.5
py -3 "Database Codes/study_index/search.py" --issue NPRR1348
py -3 "Database Codes/study_index/search.py" "firm fuel" --count

# vocabulary and coverage
py -3 "Database Codes/study_index/search.py" --terms LFL
py -3 "Database Codes/study_index/search.py" --stats
```

Add `--json` to any command for machine-readable output.

## Sources indexed

```
Documents Database/ERCOT.MKT.RULES/<CAT>/<ID>/Quick runs/<ID> Profile.json
Documents Database/ERCOT.MKT.RULES/<CAT>/<ID>/Quick runs/<ID> Summary.json
Documents Database/ERCOT.STKHDR.MEETS/<CMTE>/<DATE>/Quick runs/<..> Profile.json
Database Codes/reference_info/ercot_glossary.json
Database Codes/reference_info/ercot_market_keywords.json
```

## Freshness

`run_routine.py` rebuilds the index as **step 36 of 37** — after the profile,
summarize, stakeholder-section and `documents-submitted` steps, and before the
web rebuild. That position is load-bearing, for two reasons:

1. **The profilers rewrite `Profile.json` in place.** A build during
   `profile_ercot_*.py` captures a torn snapshot — observed: three builds minutes
   apart reported 18,200 / 15,437 / 15,216 documents mid-run.
2. **`source_documents` is not written by the profilers at all.** They rewrite
   the profile without that key; `gen_mkt_doc_summaries.py` (step 25) adds the
   per-document array back. A build anywhere between the profilers and step 25
   indexes every issue but **zero documents**, so document-level search silently
   returns nothing.

`build_index.py` detects case 2 and prints a `WARNING`, also stored in the
`warning` meta row, so `search.py --stats` shows it. If you see that warning, the
issue and meeting search still work — only document-level search is empty.

`search.py --stats` reports `built_at` and any `warning`.

## Data quirks handled here

- **Dates.** Most profiles record ISO dates, a few record free text
  ("April 30,2014", "14 May 2002", "October 12 , 2016", "Unknown"). `norm_date()`
  normalises to ISO so dates sort and filter; `issues.date_posted_raw` and
  `issue_timeline.date_raw` keep the original.
- **Sections.** Recorded however the source phrased them: a number ("2.1"), a
  title ("Definitions"), or several run together ("3.14.3.1 Emergency Response
  Service Procurement 3.14.3.3 ..."). Each embedded number is extracted into its
  own `section_num` row; 1,568 of 1,712 issues have at least one.
- **Shape drift.** The six category profilers and the meeting profiler disagree
  on whether a field is a string, a list, or a list of dicts. `as_text()`
  flattens recursively rather than breaking on the next schema change.
- **Encoding.** Some summaries carry mojibake; all reads use
  `errors="replace"`.

## Known coverage limits

- The index holds the derived summaries, **not** the full text of the source
  PDFs. A topic mentioned only in a PDF body is not findable here.
- 144 issues have no extractable section number, so `--section` cannot see them.
- Several meeting profiles have empty `topics` / `agenda_items`.
- `ERCOT.PUBAPI`, `HOT.TOPICS` and `STATS.ILLUSTRATOR` are not indexed.

The `Study-a-Topic` skill (`.claude/skills/Study a Topic.md`) wraps this CLI into
a research workflow and is required to state these limits in any brief it writes.
