"""
Migrate NPRR and SCR document files from the old OneDrive location
to the new local E: location.

Only moves files that do NOT already exist at the destination.
Removes the source file after a successful move.
Prints a summary at the end.
"""

import os
import shutil
from pathlib import Path

MIGRATIONS = [
    {
        "label": "NPRR",
        "src":   Path(r"C:\Users\chunl\OneDrive\Documents\Business Ventures\Power.Talks\Documents Database\ERCOT.MKT.RULES\NPRR"),
        "dst":   Path(r"E:\wamp64\www\Power.Talks\Documents Database\ERCOT.MKT.RULES\NPRR"),
    },
    {
        "label": "SCR",
        "src":   Path(r"C:\Users\chunl\OneDrive\Documents\Business Ventures\Power.Talks\Documents Database\ERCOT.MKT.RULES\SCR"),
        "dst":   Path(r"E:\wamp64\www\Power.Talks\Documents Database\ERCOT.MKT.RULES\SCR"),
    },
]

def migrate(src: Path, dst: Path, label: str):
    if not src.exists():
        print(f"[{label}] Source not found: {src}")
        return 0, 0, 0

    moved = skipped = errors = 0

    for src_file in src.rglob("*"):
        if not src_file.is_file():
            continue

        rel = src_file.relative_to(src)
        dst_file = dst / rel

        if dst_file.exists():
            skipped += 1
            continue

        dst_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.move(str(src_file), str(dst_file))
            print(f"  [MOVED] {rel}")
            moved += 1
        except Exception as exc:
            print(f"  [ERR]   {rel}: {exc}")
            errors += 1

    return moved, skipped, errors


total_moved = total_skipped = total_errors = 0

for m in MIGRATIONS:
    print(f"\n{'='*60}")
    print(f"{m['label']}  {m['src']}  ->  {m['dst']}")
    print(f"{'='*60}")
    mv, sk, er = migrate(m["src"], m["dst"], m["label"])
    print(f"  Moved: {mv}  |  Already at destination: {sk}  |  Errors: {er}")
    total_moved   += mv
    total_skipped += sk
    total_errors  += er

print(f"\n{'='*60}")
print(f"Total moved : {total_moved}")
print(f"Total skipped (already exist): {total_skipped}")
print(f"Total errors: {total_errors}")
