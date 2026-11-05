#!/usr/bin/env python3
"""Keep the committee list current as ERCOT's stakeholder structure changes.

The downloader's COMMITTEES dict is a hand-maintained list of committees whose
*document pages* we scrape, and it goes stale: ERCOT stands up working groups
(CIPWG, TWG), renames them and retires others, and until someone edits that
dict a new group's meetings have nowhere to be filed. The Webex recorder hit
this first -- CIPWG and TWG recordings were headed for `_unfiled/<date>`.

This module derives the live committee set from the calendar log the logger
already writes, and creates the missing `ERCOT.STKHDR.MEETS/<ACRONYM>/`
folders, so a committee that appears on ERCOT's calendar is filed correctly on
the next run without anyone editing code.

Where the names come from: the logger stores each meeting's committee name
from ERCOT's calendar and marks it `group_verified` when the meeting title's
acronym corroborates it (see ercot_calendar_logger.verify_group). A verified
pair is exactly what is wanted here -- an acronym together with its full name.

Discovery is stricter than that verification, though. Verification accepts an
acronym whose letters merely run in order through the name, which is right for
keeping ERCOT's own label but too loose for inventing a committee: "Batch/CTP
Workshop 4a" carries the TXSETLP group name, and C-T-P does run through
"Texas Standard Electronic TransacTions/Load Profiling", so a loose test would
have created a bogus CTP committee. Here the acronym must BE the name's
initials, or the name must start with it.

Outputs:
    Documents Database/ERCOT.STKHDR.MEETS/_committees.json
        {"generated": …, "committees": {"CIPWG": {"name": …, "first_seen": …,
                                                  "in_downloader_registry": false}}}

Usage:
    python committee_registry.py                 # report, create nothing
    python committee_registry.py --create        # create folders for new ones
    python committee_registry.py --create --quiet
"""
from __future__ import annotations

import argparse
import glob
import importlib.util
import json
import re
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[1]
MEETS_ROOT = PROJECT_ROOT / "Documents Database" / "ERCOT.STKHDR.MEETS"
CALENDAR_LOG = MEETS_ROOT / "_calendar_log"
LEDGER = MEETS_ROOT / "_committees.json"

sys.path.insert(0, str(HERE))

# Words that carry no initial in an ERCOT committee name.
_STOP = {"of", "and", "the", "for", "to", "a", "in", "on", "at"}


# ─── THE STRICT TEST ─────────────────────────────────────────────────────────
def initials(phrase: str) -> str:
    return "".join(w[0] for w in re.findall(r"[A-Za-z&]+", phrase or "")
                   if w.lower() not in _STOP).upper()


def names_committee(acronym: str, phrase: str) -> bool:
    """True only when `phrase` really is the expansion of `acronym`: either its
    initials spell the acronym, or it already starts with it (ERCOT writes some
    names as "IBRWG Inverter-Based Resource Working Group")."""
    if not acronym or not phrase:
        return False
    letters = re.sub(r"[^A-Z0-9]", "", acronym.upper())
    if not letters:
        return False
    if re.sub(r"[^A-Za-z]", "", phrase).upper().startswith(letters):
        return True
    return initials(phrase) == letters


# ─── SOURCES ─────────────────────────────────────────────────────────────────
def discover_from_calendar_log() -> dict[str, str]:
    """{acronym: full name} for every committee the calendar log shows with a
    verified name."""
    try:
        import ercot_calendar_logger as cl
    except ImportError:
        return {}
    found: dict[str, str] = {}
    for path in sorted(glob.glob(str(CALENDAR_LOG / "*.json"))):
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for m in data.get("meetings", []):
            group = m.get("group")
            if not group or not m.get("group_verified"):
                continue
            for acronym in cl.title_acronyms(m.get("title", "")):
                if names_committee(acronym, group):
                    found.setdefault(acronym, group)
                    break
    return found


def downloader_registry() -> set[str]:
    """Acronyms the document downloader already scrapes."""
    try:
        spec = importlib.util.spec_from_file_location(
            "_stkhdr_dl", HERE / "download_ercot_stkhdr.py")
        mod = importlib.util.module_from_spec(spec)
        sys.modules["_stkhdr_dl"] = mod
        spec.loader.exec_module(mod)
        return set(mod.COMMITTEES)
    except Exception:
        return set()


def folders_on_disk() -> set[str]:
    if not MEETS_ROOT.is_dir():
        return set()
    return {p.name for p in MEETS_ROOT.iterdir()
            if p.is_dir() and not p.name.startswith("_")}


def load_ledger() -> dict:
    if LEDGER.exists():
        try:
            return json.loads(LEDGER.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pass
    return {"generated": "", "committees": {}}


def known_committees() -> set[str]:
    """Every acronym this project can file a meeting under: the downloader's
    registry, the folders on disk, and anything the ledger has recorded. This
    is what callers should use instead of the static dict."""
    return downloader_registry() | folders_on_disk() | set(load_ledger().get("committees", {}))


# ─── SYNC ────────────────────────────────────────────────────────────────────
def sync(create: bool = False) -> dict:
    discovered = discover_from_calendar_log()
    registry = downloader_registry()
    on_disk = folders_on_disk()
    ledger = load_ledger()
    entries = ledger.get("committees", {})
    today = datetime.now().strftime("%Y-%m-%d")

    created, recorded = [], []
    for acronym, name in sorted(discovered.items()):
        entry = entries.get(acronym)
        if entry is None:
            entry = {"name": name, "first_seen": today}
            recorded.append(acronym)
        else:
            entry["name"] = name
        entry["in_downloader_registry"] = acronym in registry
        entries[acronym] = entry
        if acronym not in on_disk and create:
            (MEETS_ROOT / acronym).mkdir(parents=True, exist_ok=True)
            created.append(acronym)

    result = {
        "discovered": discovered,
        "new_folders": created,
        "missing_folders": sorted(set(discovered) - on_disk - set(created)),
        "newly_recorded": recorded,
        "not_in_registry": sorted(set(discovered) - registry),
        "registry_only": sorted(registry - set(discovered)),
    }
    if create:
        ledger["generated"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        ledger["committees"] = entries
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        LEDGER.write_text(json.dumps(ledger, indent=2, ensure_ascii=False),
                          encoding="utf-8")
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--create", action="store_true",
                    help="create folders for newly discovered committees and "
                         "write the ledger")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    if not CALENDAR_LOG.is_dir():
        print(f"No calendar log at {CALENDAR_LOG} -- run ercot_calendar_logger.py first.")
        return 1

    r = sync(create=args.create)
    verb = "created" if args.create else "would create"
    print(f"{len(r['discovered'])} committee(s) on ERCOT's calendar; "
          f"{verb} {len(r['new_folders']) or len(r['missing_folders'])} folder(s)")
    for acronym in (r["new_folders"] or r["missing_folders"]):
        print(f"    + {acronym:<9} {r['discovered'][acronym][:60]}")
    if r["not_in_registry"] and not args.quiet:
        print("\nactive on the calendar but not in the downloader's COMMITTEES "
              "registry (no document scraping, meetings still file correctly):")
        for acronym in r["not_in_registry"]:
            print(f"    {acronym:<9} {r['discovered'][acronym][:60]}")
    if r["registry_only"] and not args.quiet:
        print(f"\nin the registry with no meeting on the current calendar "
              f"({len(r['registry_only'])}): {' '.join(r['registry_only'])}")
    if args.create:
        print(f"\nledger: {LEDGER}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
