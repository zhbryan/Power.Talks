#!/usr/bin/env python3
r"""
Shared ERCOT ballot-tally extraction.

ERCOT committee ballots (PRS / WMS / RMS / ROS / COPS / TAC / CFSG) are .xls
workbooks with a single "Vote" sheet laid out like this:

    row 3   B: "WMS Motion:  To request PRS continue to table NPRR1343 ..."
            G: "Motion Carries"
    row 8   F: "Present"   G: "Yes"   H: "No"   I: "Abstain"
    ...     one block of member rows per market segment
    row 59  B: "All Sectors Voting Totals"
    row 61  F: 26.0        G: 7.5     H: 0.0    I: 0.0      <- the real tally

The tallies are segment-weighted, so they are fractional (7.5, 4.33, ...) and
abstentions are excluded from the pass percentage: pct = Yes / (Yes + No).

The earlier implementation never opened the workbook. It scraped printable
byte runs out of the raw .xls, joined them, and regex'd for r'(\d+)\s*For',
which happily matched the rule number inside the motion text — "table
NPRR1343 for further review" was read as "1343 For". Every other ballot in
the same timeline matched some other unrelated digit upstream of the word
"for". Parse the cells instead.

Requires: xlrd (for .xls), openpyxl (for .xlsx).
"""

import os
import re

# ─── SHEET READING ───────────────────────────────────────────────────────────
def _rows_xls(path):
    import xlrd
    sheet = xlrd.open_workbook(path).sheet_by_index(0)
    return [[sheet.cell_value(r, c) for c in range(sheet.ncols)]
            for r in range(sheet.nrows)]

def _rows_xlsx(path):
    import openpyxl
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    try:
        return [list(row) for row in wb[wb.sheetnames[0]].iter_rows(values_only=True)]
    finally:
        wb.close()

def _sheet_rows(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == '.xls':
        return _rows_xls(path)
    if ext in ('.xlsx', '.xlsm'):
        return _rows_xlsx(path)
    raise ValueError("not a ballot workbook: " + path)

# ─── LAYOUT DISCOVERY ────────────────────────────────────────────────────────
# Email ballots head the vote columns "Affirm" / "Object" instead of Yes / No.
_YES_HDR = ('yes', 'aye', 'for', 'in favor', 'affirm', 'affirmative')
_NO_HDR  = ('no', 'nay', 'against', 'opposed', 'object', 'objection')
_AB_HDR  = ('abstain', 'abstention', 'abstentions')

def _norm(cell):
    return '' if cell is None else str(cell).strip().lower()

def _find_columns(rows):
    """Locate the member-table header row and its columns. Both Yes and No
    must appear in the same row, which keeps the motion text and the "Total
    Abstentions" label above it from matching. Returns a dict of column
    indices plus 'row' (the header row index), or None."""
    for i, row in enumerate(rows[:40]):
        cols = {}
        for j, c in enumerate(_norm(x) for x in row):
            if c in _YES_HDR and 'yes' not in cols:
                cols['yes'] = j
            elif c in _NO_HDR and 'no' not in cols:
                cols['no'] = j
            elif c in _AB_HDR and 'ab' not in cols:
                cols['ab'] = j
            elif c == 'present' and 'present' not in cols:
                cols['present'] = j
            elif 'representative' in c and 'rep' not in cols:
                cols['rep'] = j
            elif 'entity' in c and 'entity' not in cols:
                cols['entity'] = j
        if 'yes' in cols and 'no' in cols:
            cols['row'] = i
            return cols
    return None

def _num(row, idx):
    if idx is None or idx >= len(row):
        return 0.0
    v = row[idx]
    if isinstance(v, bool):
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(str(v).strip().replace(',', ''))
    except (TypeError, ValueError):
        return 0.0

def _totals_row(rows):
    """The grand-total 'Segment Vote:' row inside the 'All Sectors Voting
    Totals' block, falling back to the summary block at the top of the sheet
    (which carries the same three numbers)."""
    marker = None
    for i, row in enumerate(rows):
        joined = ' '.join(_norm(c) for c in row if _norm(c))
        if 'all sectors voting totals' in joined:
            marker = i
            break
    window = (range(marker, min(marker + 8, len(rows))) if marker is not None
              else range(0, min(10, len(rows))))
    for i in window:
        row = rows[i]
        joined = ' '.join(_norm(c) for c in row if _norm(c))
        if 'segment vote' in joined:
            return row
    return None

# ─── TALLY RECONSTRUCTION ────────────────────────────────────────────────────
# Some ballots were saved without recalculating, so every formula cell reads
# 0.0 and only the members' own marks survive. Recompute the tally the way the
# sheet would have: each segment casts one vote (the Consumer segment casts
# "Consumer Vote Total" -- 1.0 at PRS/COPS, 1.5 at ROS/RMS/WMS), divided
# equally among its present, non-abstaining members. Abstainers drop out of
# their segment's denominator entirely, so a segment where everyone abstains
# contributes nothing. With "Divide Subsegments? = y" the Consumer vote is
# first split equally across the subsegments (Comm / Resi / Indu) that have a
# voting member. Under the TAC structure there is no weighting at all: one
# vote per present member.
_SUBSEG = ('comm', 'resi', 'indu')
_SKIP_ROW = ('segment vote', 'consumer vote total', 'divide subsegments',
             'tally total', 'all sectors voting totals')

def _cell(row, cols, key):
    j = cols.get(key)
    if j is None or j >= len(row):
        return ''
    return _norm(row[j])

def _voting_structure(rows):
    """The body named under "Voting Structure" (the cell below the label)."""
    for i, row in enumerate(rows[:12]):
        for j, c in enumerate(_norm(x) for x in row):
            if c == 'voting structure' and i + 1 < len(rows):
                below = rows[i + 1]
                if j < len(below):
                    return _norm(below[j])
    return ''

def _consumer_params(rows, header_row):
    """(consumer vote total, divide-subsegments flag)."""
    total, divide = None, False
    for row in rows[header_row:]:
        cells = [_norm(c) for c in row]
        for j, c in enumerate(cells):
            if 'consumer vote total' in c:
                total = _num(row, j + 1)
            elif 'divide subsegments' in c:
                divide = (cells[j + 1] if j + 1 < len(cells) else '') == 'y'
        if total is not None:
            break
    return total, divide

def _member(row, cols):
    """A member's presence, choice and consumer subsegment, or None if this
    row is not a member row."""
    joined = ' '.join(_norm(c) for c in row if _norm(c))
    if any(k in joined for k in _SKIP_ROW):
        return None
    pres = _cell(row, cols, 'present')
    yes  = _cell(row, cols, 'yes')
    no   = _cell(row, cols, 'no')
    ab   = _cell(row, cols, 'ab')
    if not (pres or yes or no or ab):
        return None
    if pres in ('a', 'abstain') or ab in ('a', 'x', 'abstain', 'y') or _num(row, cols.get('ab')):
        choice = 'ab'
    elif yes:
        choice = 'yes'
    elif no:
        choice = 'no'
    else:
        choice = None          # present but did not vote
    subseg = ''
    lo = cols.get('entity', 0) + 1
    hi = cols.get('rep', cols.get('present', lo))
    for j in range(lo, min(hi, len(row))):
        if _norm(row[j]) in _SUBSEG:
            subseg = _norm(row[j])
            break
    return {'choice': choice, 'subseg': subseg}

def _segments(rows, cols):
    """Member rows grouped into segments, split on the per-segment
    'Segment Vote:' subtotal rows."""
    end = len(rows)
    for i, row in enumerate(rows):
        if 'all sectors voting totals' in ' '.join(_norm(c) for c in row):
            end = i
            break
    segs, current, is_consumer = [], [], False
    for i in range(cols['row'] + 1, end):
        row = rows[i]
        joined = ' '.join(_norm(c) for c in row if _norm(c))
        if 'segment vote' in joined:
            segs.append({'members': current, 'consumer': is_consumer})
            current, is_consumer = [], False
            continue
        if _cell(row, cols, 'entity').startswith('consumer'):
            is_consumer = True
        m = _member(row, cols)
        if m:
            current.append(m)
    if current:
        segs.append({'members': current, 'consumer': is_consumer})
    return segs

def _reconstruct(rows, cols):
    """(yes, no, abstain-count) rebuilt from the member marks."""
    segs = _segments(rows, cols)
    cons_total, divide = _consumer_params(rows, cols['row'])
    unweighted = _voting_structure(rows) == 'tac'
    yes = no = 0.0
    abstentions = 0
    for seg in segs:
        abstentions += sum(1 for m in seg['members'] if m['choice'] == 'ab')
        voters = [m for m in seg['members'] if m['choice'] in ('yes', 'no')]
        if not voters:
            continue
        if unweighted:
            yes += sum(1 for m in voters if m['choice'] == 'yes')
            no  += sum(1 for m in voters if m['choice'] == 'no')
            continue
        weight = cons_total if (seg['consumer'] and cons_total) else 1.0
        if seg['consumer'] and divide:
            # The Consumer vote is split across every subsegment with a
            # present representative and then across that subsegment's present
            # representatives, abstaining or not. An abstainer's slice is
            # forfeited rather than passed to the others, so a subsegment whose
            # reps all abstained contributes nothing.
            groups = {}
            for m in seg['members']:
                groups.setdefault(m['subseg'] or '_', []).append(m)
            slice_ = weight / len(groups)
            shares = [([m for m in g if m['choice'] in ('yes', 'no')],
                       slice_ / len(g)) for g in groups.values()]
        else:
            # Every other segment redistributes: the segment's one vote is
            # divided among the members who actually voted.
            shares = [(voters, weight / len(voters))]
        for group, per in shares:
            for m in group:
                if m['choice'] == 'yes':
                    yes += per
                else:
                    no += per
    return yes, no, float(abstentions)

_CARRY_PAT = re.compile(r'motion\s+(carries|carried|passes|passed|approved)', re.IGNORECASE)
_FAIL_PAT  = re.compile(r'motion\s+(fails|failed|does\s+not\s+carry|defeated)', re.IGNORECASE)

def _verdict_cell(rows):
    """The sheet's own verdict wording, or None if it is not stated."""
    for row in rows[:15]:
        for cell in row:
            s = _norm(cell)
            if not s:
                continue
            if _CARRY_PAT.search(s):
                return 'Motion Carries'
            if _FAIL_PAT.search(s):
                return 'Motion Fails'
    return None

def _fmt(v):
    """7.0 -> '7', 7.5 -> '7.5', 4.333333 -> '4.33'."""
    r = round(float(v), 2)
    if abs(r - round(r)) < 1e-9:
        return str(int(round(r)))
    return ("%.2f" % r).rstrip('0').rstrip('.')

# ─── TEXT FALLBACK ───────────────────────────────────────────────────────────
def _verdict_from_bytes(path):
    """Last resort for a workbook no parser can open: look for the verdict
    wording in the printable byte runs. Deliberately reads no numbers — that
    is what produced the '1343 For' bug."""
    try:
        with open(path, 'rb') as f:
            data = f.read()
        text = ' '.join(s.decode('ascii', errors='ignore')
                        for s in re.findall(rb'[\x20-\x7e]{8,}', data))
    except OSError:
        return "Vote recorded"
    if _CARRY_PAT.search(text) or re.search(r'\bpassed\b', text, re.IGNORECASE):
        return "Motion Carries"
    if _FAIL_PAT.search(text) or re.search(r'\b(failed|defeated|withdrawn)\b', text, re.IGNORECASE):
        return "Motion Fails/Withdrawn"
    return "Vote recorded"

# ─── PUBLIC API ──────────────────────────────────────────────────────────────
def extract_votes(xls_path):
    """Return a one-line outcome for an ERCOT ballot workbook, e.g.
    '7.5 For, 0 Against - Motion Carries (100%)' or
    '4.33 For, 2.17 Against, 6 Abstain - Motion Carries (66.7%)'."""
    try:
        rows = _sheet_rows(xls_path)
    except Exception:
        return _verdict_from_bytes(xls_path)
    try:
        tally = read_tally(rows)
        if tally:
            yes_v, no_v, ab_v = tally
            parts = [_fmt(yes_v) + " For", _fmt(no_v) + " Against"]
            if ab_v:
                parts.append(_fmt(ab_v) + " Abstain")
            verdict = _verdict_cell(rows) or (
                'Motion Carries' if yes_v > no_v else 'Motion Fails')
            out = "%s — %s" % (', '.join(parts), verdict)
            cast = yes_v + no_v
            if cast:
                out += " (%.3g%%)" % (100.0 * yes_v / cast)
            return out
        return _verdict_cell(rows) or "Vote recorded"
    except Exception:
        return _verdict_from_bytes(xls_path)

def read_tally(rows, allow_reconstruct=True):
    """(yes, no, abstain) for a ballot sheet, preferring the workbook's own
    'All Sectors Voting Totals' row and falling back to recomputing from the
    member marks when that row was never recalculated. None if neither
    yields anything."""
    cols = _find_columns(rows)
    if not cols:
        return None
    totals = _totals_row(rows)
    cached = None
    if totals is not None:
        cached = (_num(totals, cols['yes']), _num(totals, cols['no']),
                  _num(totals, cols.get('ab')))
        if cached[0] or cached[1]:
            return cached
    if allow_reconstruct:
        yes_v, no_v, ab_v = _reconstruct(rows, cols)
        # A cached row of 0 For / 0 Against next to members who clearly marked
        # a choice means the workbook was saved without recalculating.
        if yes_v or no_v:
            return yes_v, no_v, (cached[2] if cached and cached[2] else ab_v)
    return cached if (cached and any(cached)) else None

def motion_text(xls_path):
    """The motion as worded on the ballot, or '' if it cannot be read."""
    try:
        for row in _sheet_rows(xls_path)[:15]:
            for cell in row:
                s = '' if cell is None else str(cell).strip()
                if len(s) > 20 and re.search(r'\bmotion\s*:', s, re.IGNORECASE):
                    return re.sub(r'\s+', ' ', s)
    except Exception:
        pass
    return ''

if __name__ == '__main__':
    import sys
    for p in sys.argv[1:]:
        print(os.path.basename(p))
        print("    " + extract_votes(p))
        print("    motion: " + motion_text(p))
