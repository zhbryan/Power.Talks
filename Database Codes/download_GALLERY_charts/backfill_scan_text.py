#!/usr/bin/env python3
"""backfill_scan_text.py — give older charts the page text they were found on.

    py -3 backfill_scan_text.py --dry-run
    py -3 backfill_scan_text.py

`gallery_charts.scan_text` holds the text a chart is matched on, by field, so
`retag_charts.py` can re-apply a changed vocabulary to the whole gallery
without reopening a source document. Charts extracted before that column
existed have it empty, which quietly limits them to matching on their title and
file name — the `page` field, the richest evidence a PDF chart has, is missing.

This fills it in from the PDFs already on disk: the extraction state records
which page each chart came from, so the text is read straight back out with
PyMuPDF. No AI call is involved and no PNG is re-rendered.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gallery_db as db  # noqa: E402

STATE = os.path.join(db.PROJECT_ROOT, "Documents Database", "GALLERY",
                     "_extraction_state.json")
PAGE_TEXT_LIMIT = 4000


def page_index(page_num):
    """'4' -> 3. Returns None for anything that is not a plain page number."""
    try:
        n = int(str(page_num).strip())
    except (TypeError, ValueError):
        return None
    return n - 1 if n >= 1 else None


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--force", action="store_true",
                    help="rewrite scan_text even where it is already present")
    args = ap.parse_args()

    if not os.path.exists(STATE):
        print(f"no extraction state at {STATE}")
        return 1
    with open(STATE, encoding="utf-8") as f:
        state = json.load(f)

    conn = db.connect()
    try:
        db.ensure_columns(conn)
        with conn.cursor() as cur:
            cur.execute(f"""SELECT chart_id, chart_title, doc_name, page_num, scan_text
                              FROM `{db.CHARTS_TABLE}`""")
            charts = {r[0]: {"chart_title": r[1], "doc_name": r[2],
                             "page_num": r[3], "scan_text": r[4]}
                      for r in cur.fetchall()}

        # chart_id -> the source document it came from
        origin = {}
        for rel, entry in (state.get("files") or {}).items():
            for ch in entry.get("charts") or []:
                origin[ch.get("chart_id")] = rel

        todo = [cid for cid, row in charts.items()
                if (args.force or not row["scan_text"]) and cid in origin]
        missing_origin = [cid for cid in charts if cid not in origin]

        by_doc = {}
        for cid in todo:
            by_doc.setdefault(origin[cid], []).append(cid)

        filled = no_text = unreadable = 0
        updates = []
        for rel, cids in sorted(by_doc.items()):
            path = os.path.join(db.PROJECT_ROOT, rel)
            if not os.path.isfile(path):
                unreadable += len(cids)
                if not args.quiet:
                    print(f"  !! source missing: {rel}")
                continue
            try:
                import pymupdf
                doc = pymupdf.open(path)
            except Exception as e:
                unreadable += len(cids)
                if not args.quiet:
                    print(f"  !! {os.path.basename(rel)}: {e}")
                continue
            try:
                for cid in cids:
                    row = charts[cid]
                    idx = page_index(row["page_num"])
                    text = ""
                    if idx is not None and 0 <= idx < doc.page_count:
                        try:
                            text = doc[idx].get_text() or ""
                        except Exception:
                            text = ""
                    fields = {"title": row["chart_title"] or "",
                              "doc": row["doc_name"] or ""}
                    if text.strip():
                        fields["page"] = text[:PAGE_TEXT_LIMIT]
                        filled += 1
                    else:
                        no_text += 1
                    updates.append((json.dumps(fields, ensure_ascii=False), cid))
            finally:
                doc.close()

        if not args.dry_run and updates:
            with conn.cursor() as cur:
                cur.executemany(
                    f"UPDATE `{db.CHARTS_TABLE}` SET scan_text = %s WHERE chart_id = %s",
                    updates)
            conn.commit()

        if args.quiet:
            print(f"Scan text: {len(updates)} chart(s) written, {filled} with page text"
                  + (f", {unreadable} unreadable" if unreadable else "")
                  + ("  [dry run]" if args.dry_run else ""))
            return 0

        print(f"{'[dry run] ' if args.dry_run else ''}"
              f"{len(charts)} chart(s) in the gallery, {len(todo)} needing scan_text")
        print(f"  written          : {len(updates)}")
        print(f"  with page text   : {filled}")
        if no_text:
            print(f"  no text on page  : {no_text} (image-only page)")
        if unreadable:
            print(f"  unreadable source: {unreadable}")
        if missing_origin:
            print(f"  not in extraction state: {len(missing_origin)}")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
