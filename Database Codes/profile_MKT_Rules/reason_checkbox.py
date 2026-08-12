#!/usr/bin/env python3
"""
Shared helper: extract the CHECKED "Reason for Revision" option(s) from an
ERCOT market-rule -01 filing (.docx). Used by every profile_ercot_<cat>.py.

The reason options are ActiveX Forms.TextBox controls; the sponsor types an "X"
into the chosen one(s). python-docx cannot see that "X" (it is not text) and
Word will not instantiate the controls headlessly. We read the state from each
control's embedded OLE stream: a control is CHECKED iff its `contents` stream
carries a stored 1-character value, which the MorphData format records as the
Value-count DWORD 0x80000001 (little-endian b"\\x01\\x00\\x00\\x80"). Empty
(unchecked) controls have no Value property.

This keeps only the box(es) the sponsor actually marked, rather than listing
every option. Works across both ERCOT reason templates (older "Addresses
current operational issues / Meets Strategic goals / ..." and newer "Strategic
Plan Objective 1-3 / ...") because it reads the paragraph text next to each
checked control, and across all six categories (NPRR/COPMGRR/PGRR/SCR/NOGRR/
RMGRR), which share the same form. Legacy .doc filings expose no readable
controls -> [].
"""

import io
import re
import zipfile

import olefile
from docx import Document
from docx.oxml.ns import qn

_REASON_NOTE_PAT = re.compile(r'please select', re.IGNORECASE)


def _reason_ctrl_checked(z, relmap, rid):
    tgt = relmap.get(rid)
    if not tgt:
        return False
    try:
        ole = olefile.OleFileIO(io.BytesIO(z.read('word/' + tgt.replace('.xml', '.bin'))))
        data = ole.openstream('contents').read()
        ole.close()
    except Exception:
        return False
    return b'\x01\x00\x00\x80' in data


def _clean_reason(text):
    text = re.sub(r'\s+', ' ', text).replace('�', '-').strip()
    return text.rstrip('.').strip()


def extract_checked_reasons(docx_path):
    """Return the Reason-for-Revision option(s) the sponsor checked, as the
    paragraph text next to each marked ActiveX control. Returns [] when the
    file is a legacy .doc (no readable controls), nothing is checked, or the
    reason table cannot be located."""
    if not docx_path or not docx_path.lower().endswith('.docx'):
        return []
    try:
        z = zipfile.ZipFile(docx_path)
        rels = z.read('word/_rels/document.xml.rels').decode('utf-8')
    except Exception:
        return []
    relmap = dict(re.findall(
        r'Id="(rId\d+)"[^>]*?Target="(activeX/activeX\d+\.xml)"', rels))
    if not relmap:
        return []
    try:
        doc = Document(docx_path)
    except Exception:
        return []
    for tbl in doc.tables:
        for row in tbl.rows:
            if 'reason for revision' not in ' '.join(c.text for c in row.cells).lower():
                continue
            # Dedupe merged cells; the options cell is the one bearing controls.
            seen, cells = set(), []
            for c in row.cells:
                if id(c._tc) in seen:
                    continue
                seen.add(id(c._tc)); cells.append(c)
            ctrl_cells = [c for c in cells
                          if any(True for _ in c._tc.iter(qn('w:control')))]
            if not ctrl_cells:
                continue
            cell = max(ctrl_cells, key=lambda c: len(c.text))
            checked = []
            for para in cell.paragraphs:
                t = para.text.strip()
                if not t or _REASON_NOTE_PAT.search(t):
                    continue
                rid = None
                for ctrl in para._p.iter(qn('w:control')):
                    rid = ctrl.get(qn('r:id'))
                if rid and _reason_ctrl_checked(z, relmap, rid):
                    checked.append(_clean_reason(t))
            return checked
    return []
