"""
rebuild_all_summaries.py — Force a full rebuild of every category's summaries,
ignoring the ONLY_STALE incremental check in each summarize_ercot_*.py script.

Use after a logic fix to the summarizer scripts (timeline patterns, status
inference, report layout) that should be propagated to all existing summaries.
For routine post-download refreshes, run the individual scripts instead —
their ONLY_STALE mode rebuilds only issues with new documents.
"""

import importlib.util
import os

HERE = os.path.dirname(os.path.abspath(__file__))
CATEGORIES = ["nprr", "nogrr", "pgrr", "rmgrr", "scr", "copmgrr"]


def load_module(cat):
    path = os.path.join(HERE, f"summarize_ercot_{cat}.py")
    spec = importlib.util.spec_from_file_location(f"summarize_ercot_{cat}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    for cat in CATEGORIES:
        print(f"=== {cat.upper()} START ===", flush=True)
        mod = load_module(cat)
        mod.ONLY_STALE = False
        try:
            mod.main()
        finally:
            mod.quit_word()
        print(f"=== {cat.upper()} DONE ===", flush=True)


if __name__ == "__main__":
    main()
