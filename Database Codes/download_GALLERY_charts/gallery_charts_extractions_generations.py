#!/usr/bin/env python3
"""gallery_charts_extractions_generations.py - find charts in the stakeholder
documents, save each one as a GALLERY PNG, and index it in MySQL.

What it does
------------
Walks the stakeholder-meeting document tree, looks through every **PDF** for
pages that carry a chart (bar/line/area, timeline, flow or process diagram,
org chart, ...), renders each such page to

    Documents Database/GALLERY/GC_<YYYYMMDD_HHMMSS>_<n>.png

and upserts one row per chart into `gallery.gallery_charts` plus its keyword
links into `gallery.gallery_keywords` (see `gallery_db.py` for both schemas and
for the invariant between them).

The timestamp in the file name is taken **at the moment the source file is
opened**, so every chart found in one document shares it and `<n>` is the
chart's sequence number within that document -- the name alone tells you which
extraction pass produced it and in what order.

How a chart is recognised
-------------------------
Two stages, because neither alone is good enough:

1. **Prefilter (deterministic, free).** For a PDF, the per-page vector-stroke
   count is compared against the *median for that document*: ERCOT decks draw
   the same template furniture (border, logo, footer) on every slide, so the
   raw count is dominated by boilerplate and only the excess over the deck's
   own baseline means anything. A page becomes a candidate on any of: clear
   excess strokes, a dense cluster of numeric tokens (axis ticks and data
   labels), or a large embedded raster image. This is tuned for recall -- it
   cannot tell a photo from a chart image, and does not try.

2. **Adjudication (AI, one call per document).** The candidate pages' titles,
   text and features go to Claude in a single call per document, which returns
   which of them really are charts, what kind, the chart's title, and which
   keywords apply. One call per document (not per page) is what makes a
   multi-thousand-document backfill affordable; `--ai-budget` paces it.

   With `--no-ai` the routine falls back to the prefilter's own high-confidence
   band. That is deliberately conservative: it would rather miss a chart than
   fill the Gallery with title slides and photos.

Workbooks are not a source. Until 2026-11-19 the gallery also exported chart
objects out of .xlsx/.xls through Excel COM; that was removed along with the
1,587 chart rows it had produced (see remove_excel_charts.py). The gallery is
PDF-only: one page, one chart, one decision the prefilter and the model can
both be held to.

Incremental by design
---------------------
`Documents Database/GALLERY/_extraction_state.json` records, per source file,
its size and mtime and what was extracted from it. A file whose size and mtime
are unchanged is skipped without being opened, so a nightly run only pays for
documents that are new or that ERCOT re-posted. `--rescan` forces a re-read,
`--redo-file` re-extracts one document.

Usage
-----
    py -3 gallery_charts_extractions_generations.py                 # incremental
    py -3 gallery_charts_extractions_generations.py --quiet         # one-line log
    py -3 gallery_charts_extractions_generations.py --dry-run       # no PNG, no DB
    py -3 gallery_charts_extractions_generations.py --no-ai         # prefilter only
    py -3 gallery_charts_extractions_generations.py --max-docs 50 --ai-budget 50
    py -3 gallery_charts_extractions_generations.py --group BOARD --since 2026-01-01
    py -3 gallery_charts_extractions_generations.py --verify-only   # re-check tables

Exit code is 0 on success, 1 if any document failed, 2 if the AI backend ran
out of subscription quota (the remaining documents are left for a later run).
"""
import argparse
import datetime as dt
import json
import os
import re
import statistics
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.dirname(HERE)
PROJECT_ROOT = os.path.dirname(DB_DIR)

sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(DB_DIR, "summarize_MKT_Rules"))   # ai_backend

import gallery_db  # noqa: E402

GALLERY = os.path.join(PROJECT_ROOT, "Documents Database", "GALLERY")
LOG_DIR = os.path.join(GALLERY, "routine_log")
STATE_PATH = os.path.join(GALLERY, "_extraction_state.json")
SOURCE_ROOT = os.path.join(PROJECT_ROOT, "Documents Database", "ERCOT.STKHDR.MEETS")

PDF_EXT = {".pdf"}

# Render resolution for a PDF page. 150 dpi keeps a slide legible on the web
# Gallery at roughly the size of the PNGs already in GALLERY (~150-450 KB).
RENDER_DPI = 150

AI_MODEL = os.environ.get("POWERTALKS_GALLERY_MODEL", "haiku")
AI_MAX_TOKENS = 4000

# ─── prefilter thresholds ────────────────────────────────────────────────────
# Calibrated against the pages already curated in gallery_index.json (the
# BOARD 2026-09-14 CEO-Update deck, whose pages 2/3/4 are charts and whose
# page 1 is a title slide). Tuned for recall; the AI stage supplies precision.
MIN_EXCESS_STROKES = 25     # vector content beyond the deck's template baseline
MIN_NUMERIC_TOKENS = 12     # axis ticks / data labels
MIN_IMAGE_AREA = 0.06       # fraction of the page a raster image must cover
MAX_WORDS_FOR_IMAGE_PAGE = 140   # an image page with lots of prose is not a chart
# The --no-ai band: only pages that are unmistakably plotted content.
STRONG_EXCESS_STROKES = 120
STRONG_NUMERIC_TOKENS = 20

# Chart-vs-photo thresholds for an embedded raster image (see image_signals).
# A chart is plotted on a white canvas in a handful of flat colours; a
# photograph fills its frame with a continuous range of them. Calibrated on
# the BOARD 2026-09-14 decks: charts-as-pictures measured near_white
# 0.28-0.73 with <=84 quantized colours, while photographs, logos and UI
# screenshots on the same slides measured near_white <=0.16 with 6-263.
IMG_WHITE_STRONG = 0.45
IMG_WHITE_LIKELY = 0.22
IMG_MAX_COLORS = 140

_NUMERIC = re.compile(r"^[\$\(]?[-+]?[\d,]+(\.\d+)?%?\)?$")
_BOILERPLATE = {"public", "ercot public", "ercot", ""}


def clean_title(text):
    """A usable chart title, or None.

    Slides put the page number, the classification banner and the odd stray
    glyph at the top of the text layer, so both the model and the first-line
    fallback can come back with "2" or "-". Anything with no letters, or too
    short to mean something, is not a title."""
    t = re.sub(r"\s+", " ", (text or "")).strip(" \t\r\n-–—:·•*")
    if len(t) < 4 or not re.search(r"[A-Za-z]{3}", t):
        return None
    if t.strip().lower() in _BOILERPLATE:
        return None
    return t[:500]


# ─── logging ─────────────────────────────────────────────────────────────────
class Log:
    """Console + per-run file log under GALLERY/routine_log/."""

    def __init__(self, quiet=False, path=None):
        self.quiet = quiet
        self.fh = open(path, "w", encoding="utf-8") if path else None
        self.path = path

    def __call__(self, line="", console=True):
        if self.fh:
            self.fh.write(line + "\n")
            self.fh.flush()
        if console and not self.quiet:
            try:
                print(line, flush=True)
            except (UnicodeEncodeError, OSError):
                enc = getattr(sys.stdout, "encoding", None) or "ascii"
                try:
                    sys.stdout.buffer.write((line + "\n").encode(enc, "replace"))
                    sys.stdout.flush()
                except Exception:
                    pass

    def summary(self, line):
        """Always printed, even under --quiet (the nightly routine's one line)."""
        if self.fh:
            self.fh.write(line + "\n")
            self.fh.flush()
        print(line, flush=True)

    def close(self):
        if self.fh:
            self.fh.close()


# ─── state ───────────────────────────────────────────────────────────────────
def load_state():
    if os.path.exists(STATE_PATH):
        try:
            with open(STATE_PATH, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data.get("files"), dict):
                return data
        except (ValueError, OSError):
            pass   # corrupt state is not worth failing a run over; rebuild it
    return {"description": "Per-source-file extraction state for "
                           "gallery_charts_extractions_generations.py. "
                           "A file whose size and mtime are unchanged is skipped.",
            "files": {}}


def save_state(state):
    state["updated_at"] = dt.datetime.now().isoformat(timespec="seconds")
    tmp = STATE_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    os.replace(tmp, STATE_PATH)


def file_fingerprint(path):
    st = os.stat(path)
    return {"size": st.st_size, "mtime": int(st.st_mtime)}


# ─── source discovery ────────────────────────────────────────────────────────
def parse_source_path(path):
    """Pull the committee short name and the meeting date out of the path.

    The tree is  ERCOT.STKHDR.MEETS/<GROUP>/<YYYY-MM-DD>/<file>, so the two
    path components above the file carry `doc_group` and `doc_time`. Anything
    that does not match (a loose file, a deeper `.extracted` folder) still
    yields the group when it can, and None for whatever is missing."""
    rel = os.path.relpath(path, SOURCE_ROOT).replace("\\", "/")
    parts = rel.split("/")
    group = parts[0] if len(parts) > 1 else None
    date = None
    for p in parts[1:]:
        m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", p)
        if m:
            date = p
            break
    if group and (group.startswith("_") or group.startswith(".")):
        group = None
    return group, date


def discover(args):
    """-> [(abs path, 'pdf')] for every in-scope source document."""
    out = []
    for dirpath, dirnames, filenames in os.walk(SOURCE_ROOT):
        dirnames[:] = [d for d in dirnames if not d.startswith(("_", "."))]
        for fn in filenames:
            if fn.startswith(("~$", ".")):
                continue           # Office lock files
            ext = os.path.splitext(fn)[1].lower()
            if ext not in PDF_EXT:
                continue
            kind = "pdf"
            path = os.path.join(dirpath, fn)
            group, date = parse_source_path(path)
            if args.group and (group or "").upper() != args.group.upper():
                continue
            if args.since and (not date or date < args.since):
                continue
            if args.until and (not date or date > args.until):
                continue
            out.append((path, kind))
    # newest meeting first: a nightly run spends its budget on current material
    out.sort(key=lambda t: (parse_source_path(t[0])[1] or "", t[0]), reverse=True)
    return out


# ─── chart_id / naming ───────────────────────────────────────────────────────
def open_stamp(used_stamps):
    """The timestamp that goes in the file name, taken as the file is opened.

    Two documents opened inside the same second would otherwise collide, so a
    stamp already in use is nudged forward until it is free. `used_stamps` is
    the set of stamps already taken by this run or already on disk."""
    now = dt.datetime.now()
    while True:
        s = now.strftime("%Y%m%d_%H%M%S")
        if s not in used_stamps:
            used_stamps.add(s)
            return s
        now += dt.timedelta(seconds=1)


def existing_stamps():
    """Stamps already used by PNGs in GALLERY, so a re-run never overwrites."""
    out = set()
    if os.path.isdir(GALLERY):
        for fn in os.listdir(GALLERY):
            m = re.fullmatch(r"GC_(\d{8}_\d{6})_\d+\.png", fn, re.I)
            if m:
                out.add(m.group(1))
    return out


def chart_id(stamp, seq):
    return f"GC_{stamp}_{seq}"


# ─── PDF: prefilter ──────────────────────────────────────────────────────────
def _image_metrics(blob):
    """Two cheap discriminators for 'is this picture a chart or a photograph'.

    `near_white` is the share of pixels that are essentially background: a
    chart is drawn on a white canvas, a photograph is not. `colors` counts
    colours after quantizing each channel to 8 levels: a chart uses a palette,
    a photograph uses a continuum. Returns None if the bytes will not decode."""
    import io
    import numpy as np
    from PIL import Image
    try:
        im = Image.open(io.BytesIO(blob))
        im.draft("RGB", (480, 480))        # cheap JPEG downscale where possible
        im = im.convert("RGB")
    except Exception:
        return None
    im.thumbnail((360, 360))
    a = np.asarray(im).astype(np.int16)
    if a.ndim != 3 or a.size == 0:
        return None
    gray = a.mean(axis=2)
    colors = len(np.unique((a // 32).reshape(-1, 3), axis=0))
    return {"near_white": float((gray > 238).mean()), "colors": int(colors)}


def image_signals(doc, page, area):
    """Classify the page's largest embedded picture.

    -> (n_big_images, verdict, detail) where verdict is "strong" / "likely" /
    "no" / "" (no large image). Only the largest image is measured: a slide
    whose point is a chart-shaped picture has that picture as its main content,
    and decoding every logo on the page would cost more than it tells us."""
    big = [it for it in page.get_image_info(xrefs=True)
           if (it["bbox"][2] - it["bbox"][0]) * (it["bbox"][3] - it["bbox"][1])
           > MIN_IMAGE_AREA * area]
    if not big:
        return 0, "", ""
    big.sort(key=lambda it: (it["bbox"][2] - it["bbox"][0])
             * (it["bbox"][3] - it["bbox"][1]), reverse=True)
    top = big[0]
    if not top.get("xref"):
        return len(big), "", ""
    try:
        m = _image_metrics(doc.extract_image(top["xref"])["image"])
    except Exception:
        m = None
    if not m:
        return len(big), "", ""
    detail = f"background_white={m['near_white']:.2f} palette={m['colors']}"
    if m["colors"] <= IMG_MAX_COLORS and m["near_white"] >= IMG_WHITE_STRONG:
        return len(big), "strong", detail
    if m["colors"] <= IMG_MAX_COLORS and m["near_white"] >= IMG_WHITE_LIKELY:
        return len(big), "likely", detail
    return len(big), "no", detail


def page_features(doc, page):
    """Structural signals for one PDF page."""
    strokes = 0
    for d in page.get_drawings():
        strokes += len(d.get("items", []))
    area = page.rect.width * page.rect.height or 1.0
    n_images, img_verdict, img_detail = image_signals(doc, page, area)
    words = page.get_text("words")
    numerics = sum(1 for w in words if _NUMERIC.match(w[4]))
    lines = [l.strip() for l in page.get_text().splitlines() if l.strip()]
    title = next((c for c in (clean_title(l) for l in lines[:6]) if c), "")
    return {"strokes": strokes, "images": n_images, "numerics": numerics,
            "words": len(words), "title": title[:300],
            "picture": img_verdict, "picture_detail": img_detail,
            "text": "\n".join(lines)}


def prefilter_pdf(doc):
    """-> [per-page feature dict] with `candidate` and `strong` set.

    `baseline` is the document's median stroke count: the template furniture
    every slide repeats. Only the excess over it describes the page itself."""
    pages = []
    for i in range(doc.page_count):
        f = page_features(doc, doc[i])
        f["page"] = i + 1
        pages.append(f)
    baseline = statistics.median([p["strokes"] for p in pages]) if pages else 0
    for p in pages:
        p["excess"] = p["strokes"] - baseline
        p["candidate"] = bool(
            p["excess"] >= MIN_EXCESS_STROKES
            or p["numerics"] >= MIN_NUMERIC_TOKENS
            # A chart-shaped picture counts even on a prose-heavy slide: that
            # is how an ERCOT deck carries a chart pasted in as an image, and
            # the surrounding text says nothing about it.
            or p["picture"] in ("strong", "likely")
            or (p["images"] >= 1 and p["words"] <= MAX_WORDS_FOR_IMAGE_PAGE)
        )
        # Unmistakably plotted content: used when the AI stage is unavailable.
        p["strong"] = bool(p["excess"] >= STRONG_EXCESS_STROKES
                           or p["picture"] == "strong"
                           or (p["numerics"] >= STRONG_NUMERIC_TOKENS
                               and p["excess"] >= MIN_EXCESS_STROKES))
    return pages, baseline


# ─── PDF: AI adjudication ────────────────────────────────────────────────────
AI_SYSTEM = (
    "You are indexing charts in ERCOT (Texas electricity market) stakeholder "
    "meeting documents for a searchable image gallery. You decide which pages "
    "of a document actually carry a chart, and you answer with JSON only."
)

AI_INSTRUCTIONS = """\
A page COUNTS as a chart if its main content is a data graphic or a diagram:
bar/column/line/area/scatter/pie chart, dumbbell or range comparison, heat map,
histogram, timeline or Gantt/schedule, flow chart, process or sequence diagram,
org chart, map with plotted data, or a labelled schematic.

A page does NOT count if its main content is: a title or section divider, an
agenda, a bulleted text slide, a photograph or headshot, a logo or branding
page, a plain data table with no graphic, or a screenshot of a web page or
application UI.

It also does NOT count, however graphical it looks, if it is:
- a map that only shows where things are -- offices, sites, service territory,
  "our presence" -- with no measured values plotted on it;
- a corporate or marketing graphic: capability icons, value props, award
  badges, a "who we are" layout;
- decorative shapes, arrows or callouts arranged around text.
A map counts only when it plots data, such as values shaded by zone or
quantities placed at locations.

For each page listed below, decide using its title, its extracted text and its
structural signals. Signals are hints, not proof:

- `excess_strokes` -- vector drawing beyond this document's own template
  baseline. High means the page draws its own content (axes, bars, connectors).
- `numeric_tokens` -- numbers on the page. High means axis ticks and data
  labels.
- `images` -- how many large pictures are embedded.
- `picture` -- an automatic measurement of the largest picture:
  `chart-like (strong)` or `chart-like (likely)` means it is drawn on a white
  canvas from a small palette, which is what a chart pasted in as an image
  looks like; `photo-like` means it fills its frame with many colours, like a
  photograph, a logo or a screenshot.

Note especially: when `picture` is chart-like, the page's own text is often
unrelated prose, because the chart's labels live inside the picture where no
text extraction can reach them. Trust the measurement over the missing axis
labels in that case, and let the title decide what the chart is about. When
`picture` is photo-like and nothing else on the page is plotted, say no.

Answer with a JSON array, one object per page that IS a chart, in page order:

[{"page": <int>,
  "chart_title": "<the chart's or slide's own title, verbatim, <=200 chars>",
  "chart_type": "<short description, e.g. 'stacked area chart', 'process flow diagram'>",
  "keywords": ["<term>", ...]}]

Rules for `keywords`: choose only terms from the VOCABULARY list below, copied
exactly, the ones a person searching the gallery would use for this chart.
Pick 2-6 where you can; an empty list is acceptable. Never invent a term.

Return [] if no page is a chart. Output the JSON array and nothing else.
"""


def build_ai_prompt(doc_label, pages, vocab_terms):
    """One prompt covering every candidate page of one document."""
    blocks = []
    for p in pages:
        text = p["text"]
        if len(text) > 1800:
            text = text[:1800] + " ...[truncated]"
        pic = {"strong": "chart-like (strong)", "likely": "chart-like (likely)",
               "no": "photo-like"}.get(p["picture"], "none")
        if p["picture_detail"]:
            pic += f" [{p['picture_detail']}]"
        blocks.append(
            f"--- PAGE {p['page']} ---\n"
            f"title: {p['title'] or '(none)'}\n"
            f"signals: excess_strokes={p['excess']:.0f} "
            f"numeric_tokens={p['numerics']} images={p['images']} "
            f"words={p['words']} picture={pic}\n"
            f"text:\n{text}\n"
        )
    return (
        f"DOCUMENT: {doc_label}\n"
        f"CANDIDATE PAGES: {len(pages)}\n\n"
        + AI_INSTRUCTIONS
        + "\nVOCABULARY (the only allowed keyword values):\n"
        + "\n".join(f"- {t}" for t in vocab_terms)
        + "\n\nPAGES:\n\n" + "\n".join(blocks)
    )


def parse_ai_json(text):
    """Pull the JSON array out of the model's reply.

    Tolerates a fenced block or a stray sentence around it; anything that is
    still not a list of objects raises, and the caller treats the document as
    failed rather than writing guesses."""
    t = (text or "").strip()
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z]*\s*", "", t)
        t = re.sub(r"\s*```$", "", t).strip()
    if not t.startswith("["):
        m = re.search(r"\[.*\]", t, re.S)
        if not m:
            raise ValueError(f"no JSON array in reply: {t[:200]!r}")
        t = m.group(0)
    data = json.loads(t)
    if not isinstance(data, list):
        raise ValueError("reply JSON is not an array")
    out = []
    for item in data:
        if not isinstance(item, dict) or "page" not in item:
            continue
        try:
            page = int(item["page"])
        except (TypeError, ValueError):
            continue
        kws = item.get("keywords") or []
        out.append({
            "page": page,
            "chart_title": clean_title(item.get("chart_title")),
            "chart_type": (item.get("chart_type") or "").strip()[:200] or None,
            "keywords": [str(k).strip() for k in kws if str(k).strip()],
        })
    return out


def adjudicate(doc_label, candidates, vocab, log):
    """Ask the AI backend which candidate pages are charts.

    Raises gallery_db-agnostic exceptions: AIUnavailable propagates so the
    caller can stop the run and leave the rest for the next night."""
    from ai_backend import get_client
    prompt = build_ai_prompt(doc_label, candidates, sorted(vocab.terms.values()))
    msg = get_client().messages.create(
        model=AI_MODEL, max_tokens=AI_MAX_TOKENS,
        system=AI_SYSTEM, messages=[{"role": "user", "content": prompt}],
    )
    verdicts = parse_ai_json(msg.content[0].text)
    allowed = {p["page"] for p in candidates}
    verdicts = [v for v in verdicts if v["page"] in allowed]
    log(f"      AI: {len(verdicts)}/{len(candidates)} candidate page(s) "
        f"confirmed  (in={msg.usage.input_tokens} out={msg.usage.output_tokens})")
    return verdicts


# ─── PDF: extraction ─────────────────────────────────────────────────────────
def render_page(page, out_path):
    pix = page.get_pixmap(dpi=RENDER_DPI)
    pix.save(out_path)
    return os.path.getsize(out_path)


def extract_pdf(path, stamp, vocab, concepts, args, log, ai_state):
    """-> ([chart dict], n_candidates, used_ai).

    Opens the PDF, prefilters, adjudicates, renders. `ai_state` carries the
    run's AI budget and whether the backend has gone unavailable."""
    import pymupdf
    doc = pymupdf.open(path)
    try:
        pages, baseline = prefilter_pdf(doc)
        candidates = [p for p in pages if p["candidate"]]
        log(f"      {doc.page_count} page(s), template baseline "
            f"{baseline:.0f} strokes/page, {len(candidates)} candidate(s)")
        if not candidates:
            return [], 0, False

        used_ai = False
        if args.no_ai or ai_state["exhausted"] or ai_state["budget"] <= 0:
            reason = ("--no-ai" if args.no_ai else
                      "AI unavailable" if ai_state["exhausted"] else "budget spent")
            keep = [p for p in candidates if p["strong"]]
            log(f"      {reason}: keeping {len(keep)} high-confidence page(s)")
            verdicts = [{"page": p["page"], "chart_title": p["title"] or None,
                         "chart_type": None, "keywords": []} for p in keep]
        else:
            verdicts = adjudicate(os.path.basename(path), candidates, vocab, log)
            ai_state["budget"] -= 1
            ai_state["calls"] += 1
            used_ai = True

        by_page = {p["page"]: p for p in pages}
        charts = []
        for seq, v in enumerate(sorted(verdicts, key=lambda d: d["page"]), 1):
            pg = by_page[v["page"]]
            cid = chart_id(stamp, seq)
            fname = cid + ".png"
            # Keywords: the AI's picks are filtered through the vocabulary, and
            # a page whose picks all fail falls back to a literal text scan --
            # so `keywords` can never hold a term outside gallery.keyword_id.
            resolved, dropped = vocab.resolve_all(v["keywords"])
            matched = {kid: "page-text" for kid, _ in resolved}
            if not resolved:
                # the model declined or answered off-vocabulary: fall back to a
                # literal match over the page's own text, which describes the
                # page as a whole and so is a qualifying field
                hits = concepts.match({"title": pg.get("title") or "",
                                       "page": pg["text"]})
                resolved = [(k, t) for k, t, _ in hits]
                matched = {k: w for k, _, w in hits}
            if dropped:
                log(f"        dropped {len(dropped)} out-of-vocabulary "
                    f"keyword(s): {', '.join(dropped[:4])}")
            if not args.dry_run:
                size = render_page(doc[v["page"] - 1], os.path.join(GALLERY, fname))
                log(f"        {fname}  p{v['page']}  {size/1024:.0f} KB  "
                    f"{v.get('chart_type') or 'chart'}")
            else:
                log(f"        [dry-run] {fname}  p{v['page']}  "
                    f"{v.get('chart_type') or 'chart'}")
            charts.append({
                "chart_id": cid, "file": fname,
                "matched_in": matched,
                # the page's own text is stored so this chart can be
                # re-tagged against a changed vocabulary without reopening
                # the PDF (see retag_charts.py)
                "scan_fields": {"title": v.get("chart_title") or "",
                                "doc": os.path.basename(path),
                                "page": (pg.get("text") or "")[:4000]},
                "chart_title": v["chart_title"] or clean_title(pg["title"]),
                "chart_type": v.get("chart_type"),
                "page_num": str(v["page"]), "sequence_id": seq,
                "keywords": resolved,
            })
        return charts, len(candidates), used_ai
    finally:
        doc.close()


# ─── driver ──────────────────────────────────────────────────────────────────
def run(args, log):
    if not os.path.isdir(SOURCE_ROOT):
        log.summary(f"Gallery charts: source tree not found: {SOURCE_ROOT}")
        return 1
    os.makedirs(GALLERY, exist_ok=True)

    conn = None
    if not args.dry_run:
        conn = gallery_db.connect()
        gallery_db.ensure_tables(conn)
    vocab = gallery_db.load_vocabulary(conn)
    # `concepts` is the same vocabulary with its curated aliases and the rule
    # about which chart fields may assign a keyword; `vocab` resolves the
    # model's free-text answers back onto it.
    concepts = gallery_db.load_concepts()
    log(f"Vocabulary: {len(vocab)} keyword(s) from "
        f"{gallery_db.SCHEMA}.{gallery_db.VOCAB_TABLE}; "
        f"{len(concepts)} concept(s), matching on {'/'.join(concepts.qualifying)}")

    state = load_state()
    files = state["files"]
    stamps = existing_stamps()
    docs = discover(args)
    log(f"Discovered {len(docs)} PDF source document(s) under "
        f"{os.path.relpath(SOURCE_ROOT, PROJECT_ROOT)}")

    ai_state = {"budget": args.ai_budget, "calls": 0, "exhausted": False}
    processed = skipped = failed = n_charts = 0
    quota_stop = False

    for path, kind in docs:
        rel = os.path.relpath(path, PROJECT_ROOT).replace("\\", "/")
        if args.redo_file and args.redo_file.lower() not in rel.lower():
            continue
        try:
            fp = file_fingerprint(path)
        except OSError as e:
            log(f"  !! cannot stat {rel}: {e}")
            failed += 1
            continue
        prior = files.get(rel)
        unchanged = (prior and prior.get("size") == fp["size"]
                     and prior.get("mtime") == fp["mtime"])
        # A document last seen by a --no-ai pass was only screened by the
        # high-confidence band, so it is not finished: an AI-enabled run must
        # be allowed to revisit it. Without this the cheap pass would silently
        # cap the gallery's recall for good.
        upgradable = bool(unchanged and not args.no_ai
                          and prior.get("ai_pass") is False)
        if unchanged and not upgradable and not args.rescan and not args.redo_file:
            skipped += 1
            continue
        if args.max_docs and processed >= args.max_docs:
            log(f"  -- --max-docs {args.max_docs} reached; stopping scan")
            break

        group, date = parse_source_path(path)
        log("")
        log(f"  [{processed + 1}] {rel}")
        log(f"      group={group or '?'}  meeting={date or '?'}  type={kind}")

        # The stamp is taken here, as the document is about to be opened --
        # that is what the GC_<timestamp>_<n> naming convention refers to.
        stamp = open_stamp(stamps)
        try:
            charts, n_cand, used_ai = extract_pdf(
                path, stamp, vocab, concepts, args, log, ai_state)
        except Exception as e:
            # AIUnavailable means the subscription window is spent: stop making
            # calls, leave this and every remaining document unrecorded so a
            # later run picks them up with their charts intact.
            if type(e).__name__ == "AIUnavailable":
                log(f"      !! AI backend unavailable: {e}")
                log("      -- stopping AI adjudication; remaining documents "
                    "left for the next run")
                ai_state["exhausted"] = True
                quota_stop = True
                break
            log(f"      !! failed: {e}")
            log(traceback.format_exc().rstrip())
            failed += 1
            continue

        if not args.dry_run:
            # Re-extraction mints new timestamp-based chart_ids, so the old
            # rows cannot be overwritten by upsert -- retire them, and their
            # PNGs, or this document accumulates a duplicate set per pass.
            if prior and prior.get("charts"):
                old_ids = [c.get("chart_id") for c in prior["charts"]]
                gone = gallery_db.retire_charts(conn, old_ids)
                for c in prior["charts"]:
                    stale = c.get("file")
                    sp = os.path.join(GALLERY, os.path.basename(stale)) if stale else None
                    if sp and os.path.isfile(sp):
                        try:
                            os.remove(sp)
                        except OSError as e:
                            log(f"      !! could not remove stale {os.path.basename(sp)}: {e}")
                if gone:
                    log(f"      retired {gone} row(s) from the previous pass")
            now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for c in charts:
                gallery_db.write_chart(conn, {
                    "chart_id": c["chart_id"],
                    "chart_title": c["chart_title"],
                    "doc_name": os.path.basename(path),
                    "doc_type": kind,
                    "doc_group": group,
                    "doc_time": date,
                    "page_num": c["page_num"],
                    "sequence_id": c["sequence_id"],
                }, c["keywords"], now,
                    source=("ai" if kind == "pdf" else "scan"),
                    scan_fields=c.get("scan_fields"),
                    matched_in=c.get("matched_in"))

        files[rel] = {
            **fp,
            "doc_type": kind, "doc_group": group, "doc_time": date,
            "stamp": stamp,
            "scanned_at": dt.datetime.now().isoformat(timespec="seconds"),
            "candidates": n_cand,
            # False => screened by the deterministic band only, so a later
            # AI-enabled run should revisit this document.
            "ai_pass": bool(used_ai or (args.no_ai is False and n_cand == 0)),
            "charts": [{"chart_id": c["chart_id"], "file": c["file"],
                        "page_num": c["page_num"],
                        "chart_type": c["chart_type"],
                        "keywords": [t for _, t in c["keywords"]]}
                       for c in charts],
        }
        processed += 1
        n_charts += len(charts)
        if not args.dry_run and processed % 20 == 0:
            save_state(state)       # checkpoint, so a crash keeps the progress

    if not args.dry_run:
        save_state(state)

    report = None
    if conn is not None:
        report = gallery_db.verify_invariant(conn, repair=True)
        if report["offenders"]:
            log("")
            log(f"  invariant: repaired {len(report['repaired'])} chart row(s) "
                f"whose keywords disagreed with gallery_keywords")
            for cid, extra, missing in report["offenders"][:10]:
                log(f"    {cid}: -{extra or '[]'} +{missing or '[]'}")
        if report["orphan_links"]:
            log(f"  invariant: removed links for "
                f"{len(report['orphan_links'])} missing chart(s)")
        conn.close()

    line = (f"Gallery charts: {n_charts} chart(s) from {processed} document(s)"
            f" | {skipped} unchanged")
    if ai_state["calls"]:
        line += f" | {ai_state['calls']} AI call(s)"
    if args.dry_run:
        line += " | DRY RUN"
    if failed:
        line += f" | {failed} failed"
    if quota_stop:
        line += " | STOPPED: AI quota"
    if report and report["repaired"]:
        line += f" | {len(report['repaired'])} keyword row(s) repaired"
    log.summary(line)
    if quota_stop:
        return 2
    return 1 if failed else 0


def verify_only(log):
    conn = gallery_db.connect()
    gallery_db.ensure_tables(conn)
    rep = gallery_db.verify_invariant(conn, repair=True)
    conn.close()
    log.summary(f"Gallery invariant: {rep['charts']} chart row(s), "
                f"{len(rep['offenders'])} disagreed, "
                f"{len(rep['repaired'])} repaired, "
                f"{len(rep['orphan_links'])} orphan link group(s) removed")
    for cid, extra, missing in rep["offenders"][:20]:
        log(f"  {cid}: unbacked={extra} missing={missing}")
    return 0


def prune_only(log):
    """Drop chart rows and PNGs the extraction state no longer references.

    A night killed between rendering a chart and the next state checkpoint
    leaves rows and files behind that no document claims any more. The state
    file is the authority on what the last completed pass produced, so
    anything outside it is dead weight."""
    conn = gallery_db.connect()
    gallery_db.ensure_tables(conn)
    state = load_state()
    live = {c.get("chart_id")
            for f in state["files"].values() for c in f.get("charts", [])}
    with conn.cursor() as cur:
        cur.execute(f"SELECT chart_id FROM `{gallery_db.CHARTS_TABLE}`")
        in_db = {r[0] for r in cur.fetchall()}
    orphan_rows = sorted(in_db - live)
    n_rows = gallery_db.retire_charts(conn, orphan_rows)
    conn.close()

    n_png = 0
    for fn in os.listdir(GALLERY) if os.path.isdir(GALLERY) else []:
        if not (fn.startswith("GC_") and fn.lower().endswith(".png")):
            continue
        if os.path.splitext(fn)[0] in live:
            continue
        try:
            os.remove(os.path.join(GALLERY, fn))
            n_png += 1
        except OSError as e:
            log(f"  !! could not remove {fn}: {e}")
    for cid in orphan_rows[:20]:
        log(f"  orphan row {cid}")
    log.summary(f"Gallery prune: {n_rows} orphan row(s) and {n_png} orphan "
                f"PNG(s) removed; {len(live)} chart(s) still tracked")
    return 0


def main():
    p = argparse.ArgumentParser(
        description="Extract charts from stakeholder PDFs into GALLERY "
                    "and index them in the gallery schema.")
    p.add_argument("--quiet", action="store_true",
                   help="only the one-line summary on the console "
                        "(the full log still goes to GALLERY/routine_log/)")
    p.add_argument("--dry-run", action="store_true",
                   help="detect and report only: no PNG written, no DB write")
    p.add_argument("--no-ai", action="store_true",
                   help="skip AI adjudication; keep only high-confidence pages")
    p.add_argument("--ai-budget", type=int, default=400,
                   help="max AI calls (one per document) this run may spend "
                        "(default 400, 0 disables AI)")
    p.add_argument("--max-docs", type=int, default=0,
                   help="stop after processing this many documents (0 = no cap)")
    p.add_argument("--rescan", action="store_true",
                   help="re-read every document, ignoring the unchanged check")
    p.add_argument("--redo-file",
                   help="re-extract only documents whose path contains this text")
    p.add_argument("--prune", action="store_true",
                   help="delete chart rows and PNGs no longer referenced by "
                        "the extraction state, then exit (cleans up after a "
                        "night that was interrupted mid-document)")
    p.add_argument("--group", help="limit to one committee folder, e.g. BOARD")
    p.add_argument("--since", help="only meetings on/after this date (YYYY-MM-DD)")
    p.add_argument("--until", help="only meetings on/before this date (YYYY-MM-DD)")
    p.add_argument("--verify-only", action="store_true",
                   help="only re-check and repair the keyword invariant")
    args = p.parse_args()

    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    os.makedirs(LOG_DIR, exist_ok=True)
    log_path = os.path.join(
        LOG_DIR, f"gallery_charts_{dt.datetime.now():%Y%m%d_%H%M%S}.log")
    log = Log(quiet=args.quiet, path=log_path)
    log(f"gallery_charts_extractions_generations - "
        f"{dt.datetime.now():%Y-%m-%d %H:%M:%S}")
    log("=" * 72)
    try:
        if args.verify_only:
            rc = verify_only(log)
        elif args.prune:
            rc = prune_only(log)
        else:
            rc = run(args, log)
    except Exception:
        log("UNHANDLED ERROR")
        log(traceback.format_exc().rstrip())
        rc = 1
    finally:
        log(f"Log: {log_path}", console=False)
        log.close()
    if not args.quiet:
        print(f"\nLog written to: {log_path}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
