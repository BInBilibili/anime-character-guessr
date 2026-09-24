"""Extract subject cover URLs from the local raw crawl (no network needed).

Sources:
  $ACG_WORK/data/subjects.jsonl   raw /v0/subjects/{id} responses
  <repo>\\client\\public\\gamedata\\subjects.json   the searchable set

Output: $ACG_WORK/covers_urls.json  {sid: {grid, small, medium, large}}
"""
import json, os, collections

_HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("ACG_REPO") or os.path.abspath(os.path.join(_HERE, "..", ".."))
WORK = os.environ.get("ACG_WORK") or os.path.join(_HERE, "_work")
os.makedirs(WORK, exist_ok=True)
TMP = WORK
RAW = os.path.join(TMP, "data", "subjects.jsonl")
SUBJ = os.path.join(REPO, "client", "public", "gamedata", "subjects.json")
OUT = os.path.join(TMP, "covers_urls.json")

searchable = set(json.load(open(SUBJ, encoding="utf-8")).keys())
print("searchable subjects in subjects.json:", len(searchable))

raws = {}
keys_seen = collections.Counter()
img_keys = collections.Counter()
n = 0
with open(RAW, encoding="utf-8") as fh:
    for line in fh:
        line = line.strip()
        if not line:
            continue
        n += 1
        rec = json.loads(line)
        sid = str(rec.get("id"))
        raw = rec.get("d") or rec.get("raw") or {}
        keys_seen.update(raw.keys())
        imgs = raw.get("images") or {}
        img_keys.update(imgs.keys())
        if imgs:
            raws[sid] = imgs

print("raw subject records:", n, "with images:", len(raws))
print("top-level keys:", keys_seen.most_common(12))
print("image variants:", img_keys.most_common())

hit = {s: raws[s] for s in searchable if s in raws}
miss = [s for s in searchable if s not in raws]
print("searchable with cover url:", len(hit), "| missing:", len(miss))
print("missing sample:", miss[:10])

# how many have a usable grid variant
grid = sum(1 for v in hit.values() if v.get("grid"))
print("with images.grid:", grid)
sample = list(hit.items())[:2]
for sid, v in sample:
    print("sample", sid, json.dumps(v, ensure_ascii=False))

json.dump(hit, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print("wrote", OUT, os.path.getsize(OUT), "bytes")
