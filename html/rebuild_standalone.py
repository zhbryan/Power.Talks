"""
Patch the standalone HTML by replacing the illustration.jsx entry in the bundle
with the current content of src/illustration.jsx.

Usage:  py -3 rebuild_standalone.py
"""

import json, base64, gzip, re, shutil
from pathlib import Path

STANDALONE = Path(__file__).parent / "Power.Talks (standalone).html"
SRC_DIR    = Path(__file__).parent / "src"

def compress(text: str) -> str:
    return base64.b64encode(gzip.compress(text.encode("utf-8"), compresslevel=9)).decode()

def patch():
    html = STANDALONE.read_text(encoding="utf-8")

    manifest_match = re.search(
        r'(<script type="__bundler/manifest">)(.*?)(</script>)',
        html, re.DOTALL
    )
    if not manifest_match:
        raise RuntimeError("Could not find __bundler/manifest script tag")

    manifest = json.loads(manifest_match.group(2))

    # Stable strings unique to each file — survive signature/import line changes
    ANCHORS = {
        "icons.jsx":        "window.I = {",
        "data.jsx":         "window.DATA = {",
        "illustration.jsx": "window.PaperTrailsIllustration",
        "meetingtracks.jsx":"window.MeetingTracksOrgChart",
        "sidebar.jsx":      "window.Sidebar = Sidebar",
        "topbar.jsx":       "window.Topbar = Topbar",
        "messages.jsx":     "window.MessageStream",
        "composer.jsx":     "window.Composer = Composer",
        "rightpanel.jsx":   "window.RightPanel = RightPanel",
        "tweaks.jsx":       "window.TweaksPanel",
        "app.jsx":          "ReactDOM.createRoot",
    }

    src_files = {f.name: f.read_text(encoding="utf-8") for f in SRC_DIR.glob("*.jsx")}
    updated = []

    for uuid, entry in manifest.items():
        data = base64.b64decode(entry["data"])
        if entry.get("compressed"):
            try:
                text = gzip.decompress(data).decode("utf-8", errors="replace")
            except Exception:
                continue
        else:
            text = data.decode("utf-8", errors="replace")

        for fname, src_content in src_files.items():
            anchor = ANCHORS.get(fname)
            # Primary: first-80-char fingerprint; secondary: stable anchor present in both
            if text.strip()[:80] == src_content.strip()[:80] or (anchor and anchor in text and anchor in src_content):
                manifest[uuid]["data"] = compress(src_content)
                manifest[uuid]["compressed"] = True
                updated.append(fname)
                break

    if not updated:
        print("WARNING: no source files matched entries in the manifest.")
    else:
        print(f"Updated {len(updated)} entries: {', '.join(updated)}")

    new_manifest_json = json.dumps(manifest, separators=(",", ":"))
    new_html = html[:manifest_match.start(2)] + new_manifest_json + html[manifest_match.end(2):]

    shutil.copy(STANDALONE, str(STANDALONE) + ".bak")
    STANDALONE.write_text(new_html, encoding="utf-8")
    print(f"Wrote {STANDALONE.name}  (backup saved as .bak)")

if __name__ == "__main__":
    patch()
