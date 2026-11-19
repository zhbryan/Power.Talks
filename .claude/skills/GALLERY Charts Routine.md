---
name: GALLERY-Charts-Routine
description: Set up, run, tune and troubleshoot the Power.Talks GALLERY chart routine — a scheduled job, separate from the 1 AM daily refresh, that finds charts (timelines, flow charts, bar/line/area plots, org charts) inside ERCOT stakeholder PDFs, saves each one as Documents Database/GALLERY/GC_<timestamp>_<n>.png, and indexes it in the MySQL `gallery` schema as gallery_charts + gallery_keywords.
trigger: When the user asks to extract charts from meeting documents into the GALLERY, build or rebuild the gallery_charts / gallery_keywords tables, schedule or re-schedule the gallery chart routine, backfill the chart gallery, or debug why a chart was or was not picked up.
---

# GALLERY Charts Routine

The routine's code and its full documentation live with the rest of its files,
so the two never drift apart:

**Read `Database Codes/download_GALLERY_charts/GALLERY Charts Routine.md` and
follow it.** That file is the source of truth for this skill.

Quick orientation while it loads:

| | |
|---|---|
| Extractor | `Database Codes/download_GALLERY_charts/gallery_charts_extractions_generations.py` |
| Schema / invariant | `Database Codes/download_GALLERY_charts/gallery_db.py` |
| Routine driver | `Database Codes/download_GALLERY_charts/run_gallery_routine.py` |
| Scheduling | `Database Codes/download_GALLERY_charts/register_gallery_task.ps1` |
| Output | `Documents Database/GALLERY/GC_<YYYYMMDD_HHMMSS>_<n>.png` |
| Logs | `Documents Database/GALLERY/routine_log/` |
| Tables | `gallery.gallery_charts`, `gallery.gallery_keywords` |

Two things to keep in mind before changing anything:

* This routine is **separate from `run_routine.py`** (the 1 AM daily refresh)
  on purpose — it reads thousands of documents and
  spends its own AI budget. Do not fold it back in.
* `gallery_charts.keywords` may only hold values backed by
  `gallery_keywords.keyword` for that chart, and every keyword must come from
  `gallery.keyword_id`. The code maintains this by construction; do not write
  the two tables independently.
