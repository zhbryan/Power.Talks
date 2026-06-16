"""Splice gen_data.py output into html/src/data.jsx.

For each category given on the command line, replaces the contiguous region
from its first `const <CAT>_<STATUS> = [` declaration through the closing
`];` of its last one with the freshly generated arrays from
<cat>_data_temp.txt (produced by gen_data.py).

Usage:  py -3 update_data_jsx.py SCR NOGRR ...
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = r"E:\wamp64\www\Power.Talks\html\src\data.jsx"

def splice(src, cat):
    gen_path = os.path.join(HERE, f"{cat.lower()}_data_temp.txt")
    with open(gen_path, encoding="utf-8") as f:
        gen = f.read().strip()

    blocks = list(re.finditer(rf"const {cat}_[A-Z]+ = \[.*?\];", src, re.DOTALL))
    if not blocks:
        raise SystemExit(f"no existing {cat}_* arrays found in data.jsx")
    start, end = blocks[0].start(), blocks[-1].end()

    old_n = src[start:end].count("{ n:")
    new_n = gen.count("{ n:")
    print(f"{cat}: replacing {len(blocks)} arrays, {old_n} -> {new_n} entries")

    # Array names must stay in sync with the window.DATA export list.
    old_names = set(re.findall(rf"const ({cat}_[A-Z]+) =", src[start:end]))
    new_names = set(re.findall(rf"const ({cat}_[A-Z]+) =", gen))
    if old_names != new_names:
        raise SystemExit(f"{cat}: array set changed {sorted(old_names)} -> "
                         f"{sorted(new_names)}; update window.DATA export first")

    return src[:start] + gen + src[end:]

def main():
    cats = [c.upper() for c in sys.argv[1:]]
    if not cats:
        raise SystemExit("usage: update_data_jsx.py CATEGORY [CATEGORY ...]")
    with open(DATA, encoding="utf-8") as f:
        src = f.read()
    for cat in cats:
        src = splice(src, cat)
    with open(DATA, "w", encoding="utf-8") as f:
        f.write(src)
    print("data.jsx updated")

if __name__ == "__main__":
    main()
