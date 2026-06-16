import os, json, re, sys

def gen_arrays(category, base, zero_pad=0):
    buckets = {}
    folders = sorted(
        [d for d in os.listdir(base) if re.match(rf'^{category}\d+$', d)],
        key=lambda x: int(re.search(r'\d+', x).group())
    )
    for folder in folders:
        n = int(re.search(r'\d+', folder).group())
        nstr = str(n).zfill(zero_pad) if zero_pad else str(n)
        summary_path = os.path.join(base, folder, "Quick runs", f"{category}{nstr} Summary.json")
        profile_path = os.path.join(base, folder, "Quick runs", f"{category}{nstr} Profile.json")
        title, status = "", "Approved"
        if os.path.exists(summary_path):
            with open(summary_path, encoding='utf-8') as f:
                s = json.load(f)
            if s.get('title') and s['title'] not in (f"{category}{nstr}", f"{category}{n}"):
                title = s['title']
        if os.path.exists(profile_path):
            with open(profile_path, encoding='utf-8') as f:
                p = json.load(f)
            if not title and p.get('title'):
                title = p['title']
            if p.get('status'):
                status = p['status']
        title = title.replace('"', "'")
        entry = f'  {{ n: {n}, title: "{title}" }},'
        buckets.setdefault(status, []).append(entry)
    return buckets

DB = r"E:\wamp64\www\Power.Talks\Documents Database\ERCOT.MKT.RULES"

# Zero-padded issue numbers in Quick runs filenames (e.g. COPMGRR051)
ZERO_PAD = {"COPMGRR": 3}

for cat in (sys.argv[1:] or ["NOGRR", "RMGRR"]):
    cat = cat.upper()
    buckets = gen_arrays(cat, os.path.join(DB, cat), ZERO_PAD.get(cat, 0))
    lines = []
    for status in ["Pending", "Approved", "Withdrawn", "Rejected"]:
        items = buckets.get(status, [])
        if items:
            lines.append(f"const {cat}_{status.upper()} = [")
            lines.extend(items)
            lines.append("];")
            lines.append("")
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"{cat.lower()}_data_temp.txt")
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    counts = {k: len(v) for k, v in buckets.items()}
    print(f"{cat}: {counts}")
