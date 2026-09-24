"""Phase 3: compact the raw JSONL dumps into the small JSON files the site ships.

Inputs (from fetch_chars.py / fetch_data.py, in ACG_WORK):
  chars_data.jsonl       {id, raw, webp, bytes}
  data/char_subjects.jsonl {id, d:[{id,staff,type,...}]}
  data/char_persons.jsonl  {id, d:[{id,name,subject_type,...}]}
  data/subjects.jsonl      {id, d:{...}}
  data/subject_chars.jsonl {id, d:[{id,name,relation,...}]}

Outputs -> <repo>/client/public/gamedata/
  chars.json      { "<cid>": [name, nameCn, nameEn, gender, popularity, "shard/base", summary] }
  char_subj.json  { "<cid>": [[subjectId, "staff", type], ...] }
  char_pers.json  { "<cid>": [vaName, ...] }
  subjects.json   { "<sid>": [name, nameCn, date, type, locked, ratingScore, ratingTotal, metaTags[], "shard/base"|""] }
  subj_tags.json  { "<sid>": [["tag", count], ...] }
  subj_chars.json { "<sid>": [[cid, "relation"], ...] }
  search.json     [ [cid, name, nameCn, nameEn, aliases[]], ... ]   (sorted by popularity desc)
"""
import json, os, re, sys, time, hashlib
from collections import defaultdict

_HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("ACG_REPO") or os.path.abspath(os.path.join(_HERE, "..", ".."))
WORK = os.environ.get("ACG_WORK") or os.path.join(_HERE, "_work")
os.makedirs(WORK, exist_ok=True)
TMP = WORK
OUT = os.path.join(REPO, "client", "public", "gamedata")
UA_NOTE = "anime-character-guessr local mirror"

# Date of the Bangumi snapshot (the day the crawl finished, UTC+8). Bump it
# whenever the data is re-crawled: it is published in version.json and shown on
# the home page as "data snapshot <DATE>", so it must stay truthful.
DATA_CUTOFF = "2026-09-23"


def jl(path):
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except Exception:
                pass


def infobox_get(ib, key):
    if not isinstance(ib, list):
        return None
    for it in ib:
        if isinstance(it, dict) and it.get("key") == key:
            return it.get("value")
    return None


def main():
    os.makedirs(OUT, exist_ok=True)
    t0 = time.time()

    # ---------- characters ----------
    chars = {}
    search = []
    allowed = set()
    for rec in jl(os.path.join(TMP, "chars_data.jsonl")):
        cid = rec.get("id")
        raw = rec.get("raw") or {}
        webp = rec.get("webp")  # chars/XX/base.webp
        if not cid or not webp:
            continue
        allowed.add(cid)
        # Shard directory must be lowercased. shard_of() preserves the original case of
        # the image basename, so it produced variants like "bX"/"bx"/"BX"; Windows treats
        # those as one directory and git (core.ignorecase=true) recorded whichever existed
        # first, while GitHub Pages runs on case-sensitive Linux -> 404 for the others.
        # The basename itself must keep its exact case (it mirrors Bangumi's filename).
        if webp.startswith("chars/"):
            rest = webp[len("chars/"):-len(".webp")]
            shard, _, base = rest.partition("/")
            img = shard.lower() + "/" + base
        else:
            img = None
        ib = raw.get("infobox")
        name = raw.get("name") or ""
        nameCn = infobox_get(ib, "简体中文名") or name
        nameEn = name
        aliases = infobox_get(ib, "别名")
        alias_list = []
        if isinstance(aliases, list):
            for a in aliases:
                if isinstance(a, dict) and a.get("v"):
                    alias_list.append(str(a["v"]))
            en = next((a["v"] for a in aliases if isinstance(a, dict) and a.get("k") == "英文名"), None)
            ro = next((a["v"] for a in aliases if isinstance(a, dict) and a.get("k") == "罗马字"), None)
            nameEn = en or ro or name
        stat = raw.get("stat") or {}
        pop = int(stat.get("collects") or 0) + int(stat.get("comments") or 0)
        g = raw.get("gender")
        gender = g if g in ("male", "female") else "?"
        summary = (raw.get("summary") or "").replace("\r\n", "\n").strip()
        chars[str(cid)] = [name, nameCn, nameEn, gender, pop, img, summary]
        search.append([cid, name, nameCn, nameEn, alias_list, pop])

    print("characters: %d" % len(chars), flush=True)

    # ---------- char -> subjects ----------
    char_subj = {}
    for rec in jl(os.path.join(TMP, "data", "char_subjects.jsonl")):
        cid = rec.get("id")
        if cid not in allowed:
            continue
        rows = []
        for x in rec.get("d") or []:
            if not isinstance(x, dict) or not x.get("id"):
                continue
            if x.get("staff") not in ("主角", "配角"):
                continue
            rows.append([int(x["id"]), x.get("staff"), x.get("type")])
        char_subj[str(cid)] = rows
    print("char_subj: %d chars" % len(char_subj), flush=True)

    # ---------- char -> voice actors ----------
    char_pers = {}
    for rec in jl(os.path.join(TMP, "data", "char_persons.jsonl")):
        cid = rec.get("id")
        if cid not in allowed:
            continue
        names = sorted({str(p["name"]) for p in (rec.get("d") or [])
                        if isinstance(p, dict) and p.get("name") and p.get("subject_type") in (2, 4)})
        char_pers[str(cid)] = names
    print("char_pers: %d chars" % len(char_pers), flush=True)

    # ---------- subjects ----------
    subjects, subj_tags, covers_used = {}, {}, set()
    for rec in jl(os.path.join(TMP, "data", "subjects.jsonl")):
        sid = rec.get("id")
        d = rec.get("d") or {}
        if not sid:
            continue
        rating = d.get("rating") or {}
        # cover: only ship a path when the webp actually exists on disk, so the UI
        # falls back to its "no image" placeholder instead of requesting a 404.
        cimgs = d.get("images") or {}
        curl = cimgs.get("grid") or cimgs.get("small") or cimgs.get("common") or ""
        cover = ""
        if curl:
            cbase = curl.rsplit("/", 1)[-1].rsplit(".", 1)[0]
            crel = cbase[-5:-3].lower() + "/" + cbase
            if os.path.exists(os.path.join(REPO, "client", "public", "covers", crel + ".webp")):
                cover = crel
                covers_used.add(crel)
        subjects[str(sid)] = [
            d.get("name") or "",
            d.get("name_cn") or d.get("name") or "",
            d.get("date") or "",
            d.get("type"),
            bool(d.get("locked")),
            round(float(rating.get("score") or 0), 2),
            int(rating.get("total") or 0),
            list(d.get("meta_tags") or []),
            cover,
        ]
        tg = []
        for t in (d.get("tags") or []):
            if isinstance(t, dict) and t.get("name"):
                tg.append([str(t["name"]), int(t.get("count") or 0)])
        if tg:
            subj_tags[str(sid)] = tg
    print("subjects: %d (with tags: %d, with cover: %d)" % (
        len(subjects), len(subj_tags), len(covers_used)), flush=True)

    # ---------- subject -> characters ----------
    subj_chars = {}
    for rec in jl(os.path.join(TMP, "data", "subject_chars.jsonl")):
        sid = rec.get("id")
        if not sid:
            continue
        rows = []
        for c in rec.get("d") or []:
            if not isinstance(c, dict) or not c.get("id"):
                continue
            if c.get("relation") not in ("主角", "配角"):
                continue
            if int(c["id"]) not in allowed:
                continue  # keep only characters we actually ship art+data for
            rows.append([int(c["id"]), c.get("relation")])
        subj_chars[str(sid)] = rows
    print("subj_chars: %d subjects" % len(subj_chars), flush=True)

    # ---------- search index (popularity desc) ----------
    search.sort(key=lambda r: -r[5])
    search = [r[:5] for r in search]

    def dump(name, obj):
        p = os.path.join(OUT, name)
        with open(p, "w", encoding="utf-8") as fh:
            json.dump(obj, fh, ensure_ascii=False, separators=(",", ":"))
        mb = os.path.getsize(p) / 1048576
        print("  %-16s %8.2f MB" % (name, mb), flush=True)
        return mb

    total = 0
    total += dump("chars.json", chars)
    total += dump("char_subj.json", char_subj)
    total += dump("char_pers.json", char_pers)
    total += dump("subjects.json", subjects)
    total += dump("subj_tags.json", subj_tags)
    total += dump("subj_chars.json", subj_chars)
    total += dump("search.json", search)

    # ---------- data version ----------
    # The client fetches the 7 files as "?v=<hash>" so the browser can cache them
    # forever: GitHub Pages ignores If-None-Match, so revalidating them would mean
    # re-downloading 31 MB on every page load. A new hash = new URLs = fresh data.
    h = hashlib.sha256()
    for fn in ("chars", "char_subj", "char_pers", "subjects", "subj_tags", "subj_chars", "search",
               "indices"):
        with open(os.path.join(OUT, fn + ".json"), "rb") as fh:
            h.update(fh.read())
    ver = h.hexdigest()[:12]
    meta = {"v": ver, "cutoff": DATA_CUTOFF, "chars": len(chars), "subjects": len(subjects)}
    with open(os.path.join(OUT, "version.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, separators=(",", ":"))
    print("  %-16s %s cutoff=%s chars=%d subjects=%d"
          % ("version.json", ver, DATA_CUTOFF, len(chars), len(subjects)), flush=True)
    print("TOTAL %.2f MB in %.0fs" % (total, time.time() - t0), flush=True)


if __name__ == "__main__":
    main()
