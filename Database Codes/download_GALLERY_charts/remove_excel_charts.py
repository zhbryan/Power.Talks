#!/usr/bin/env python3
"""remove_excel_charts.py — take Excel workbooks out of the GALLERY.

    py -3 remove_excel_charts.py --dry-run     # report, touch nothing
    py -3 remove_excel_charts.py               # quarantine PNGs, clear rows+state
    py -3 remove_excel_charts.py --purge       # same, but delete the PNGs outright

One-time migration, 2026-11-19: the gallery is sourced from stakeholder PDFs
only. Workbook charts are no longer extracted (see
gallery_charts_extractions_generations.py), so the rows, links, PNGs and
extraction-state entries they left behind have to go too, or the gallery keeps
serving charts nothing can regenerate.

PNGs are MOVED to a quarantine folder rather than deleted, because
`Documents Database/` is outside version control and a wrong call here is not
recoverable. Delete the folder by hand, or re-run with --purge, once you are
satisfied. The database rows and state entries ARE deleted: they are derived
data that the PDF-only extractor would never write again.
"""
import argparse
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gallery_db as db  # noqa: E402

GALLERY = os.path.join(db.PROJECT_ROOT, "Documents Database", "GALLERY")
STATE = os.path.join(GALLERY, "_extraction_state.json")
QUARANTINE = os.path.join(db.PROJECT_ROOT, "Documents Database", "_retired_excel_charts")
EXCEL_EXT = {".xlsx", ".xlsm", ".xls"}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--purge", action="store_true",
                    help="delete the PNGs instead of moving them to quarantine")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    conn = db.connect()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT chart_id FROM `{db.CHARTS_TABLE}` WHERE doc_type = 'excel'")
            chart_ids = [r[0] for r in cur.fetchall()]
            cur.execute(f"""SELECT COUNT(*) FROM `{db.LINKS_TABLE}` g
                             JOIN `{db.CHARTS_TABLE}` c ON c.chart_id = g.chart_id
                            WHERE c.doc_type = 'excel'""")
            n_links = cur.fetchone()[0]
            cur.execute(f"SELECT COUNT(*) FROM `{db.CHARTS_TABLE}`")
            n_charts_before = cur.fetchone()[0]

        pngs = [cid + ".png" for cid in chart_ids]
        on_disk = [p for p in pngs if os.path.isfile(os.path.join(GALLERY, p))]
        bytes_on_disk = sum(os.path.getsize(os.path.join(GALLERY, p)) for p in on_disk)

        state = None
        n_state = 0
        if os.path.exists(STATE):
            with open(STATE, encoding="utf-8") as f:
                state = json.load(f)
            n_state = sum(1 for k, v in (state.get("files") or {}).items()
                          if (v.get("doc_type") or "").lower() == "excel"
                          or os.path.splitext(k)[1].lower() in EXCEL_EXT)

        print(f"{'[dry run] ' if args.dry_run else ''}Excel in the gallery:")
        print(f"  chart rows          : {len(chart_ids)} of {n_charts_before}")
        print(f"  keyword links       : {n_links}")
        print(f"  PNGs on disk        : {len(on_disk)} ({bytes_on_disk / 1e6:.1f} MB)")
        print(f"  extraction state    : {n_state} file entries")
        if args.dry_run:
            print(f"\n  PNGs would be {'deleted' if args.purge else 'moved to ' + QUARANTINE}")
            return 0
        if not chart_ids and not n_state and not on_disk:
            print("  nothing to do")
            return 0

        # ── PNGs first: if this fails, the database still describes them ─────
        moved = failed = 0
        if on_disk and not args.purge:
            os.makedirs(QUARANTINE, exist_ok=True)
        for name in on_disk:
            src = os.path.join(GALLERY, name)
            try:
                if args.purge:
                    os.remove(src)
                else:
                    shutil.move(src, os.path.join(QUARANTINE, name))
                moved += 1
            except OSError as e:
                failed += 1
                print(f"  !! {name}: {e}")

        # ── database ─────────────────────────────────────────────────────────
        with conn.cursor() as cur:
            cur.execute(f"""DELETE g FROM `{db.LINKS_TABLE}` g
                             JOIN `{db.CHARTS_TABLE}` c ON c.chart_id = g.chart_id
                            WHERE c.doc_type = 'excel'""")
            deleted_links = cur.rowcount
            cur.execute(f"DELETE FROM `{db.CHARTS_TABLE}` WHERE doc_type = 'excel'")
            deleted_charts = cur.rowcount
        conn.commit()

        # ── extraction state ─────────────────────────────────────────────────
        if state is not None:
            files = state.get("files") or {}
            keep = {k: v for k, v in files.items()
                    if (v.get("doc_type") or "").lower() != "excel"
                    and os.path.splitext(k)[1].lower() not in EXCEL_EXT}
            dropped = len(files) - len(keep)
            state["files"] = keep
            tmp = STATE + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=1, ensure_ascii=False)
            os.replace(tmp, STATE)
        else:
            dropped = 0

        with conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM `{db.CHARTS_TABLE}`")
            n_after = cur.fetchone()[0]

        print(f"\n  deleted {deleted_charts} chart row(s), {deleted_links} link(s)")
        print(f"  {'purged' if args.purge else 'quarantined'} {moved} PNG(s)"
              + (f", {failed} failed" if failed else ""))
        print(f"  dropped {dropped} extraction-state entr(ies)")
        print(f"  gallery now holds {n_after} chart(s)")
        if not args.purge and moved:
            print(f"\n  PNGs are in {QUARANTINE}")
            print("  delete that folder once you are satisfied.")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
