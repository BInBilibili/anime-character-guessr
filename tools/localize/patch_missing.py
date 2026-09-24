"""Fill the gaps left by the 2860 failed /subjects/{id}/characters calls.

Targets the two subjects that the built-in preset indexes need but that ended up
with an empty local roster:
  18011  英雄联盟            (LoL, 156 characters)
  504678 摇滚乃是淑女的爱好   (37 characters)

- re-fetch /v0/subjects/{sid}/characters -> data/subject_chars.jsonl (append)
- for every character we do not ship yet: /v0/characters/{cid} + image -> WebP,
  /characters/{cid}/subjects -> data/char_subjects.jsonl, /persons -> data/char_persons.jsonl
- shard dirs are written LOWERCASE (Windows is case-insensitive, Pages is not)
"""
import io
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from PIL import Image

TMP = os.environ["ACG_TMP"]
REPO = os.environ["ACG_REPO"]
PROXY = os.environ.get("HTTPS_PROXY") or "http://127.0.0.1:7890"
SIDS = ["18011", "504678"]
OUT_IMG = os.path.join(REPO, "client", "public", "chars")
MAX_EDGE = 320
QUALITY = 82

S = requests.Session()
S.proxies = {"http": PROXY, "https": PROXY}
S.headers.update({"User-Agent": "acg-guessr-local-build/1.0"})


def api(path, params=None, tries=4):
    for a in range(tries):
        try:
            r = S.get("https://api.bgm.tv" + path, params=params, timeout=40)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 404:
                return None
            time.sleep(1.5 ** a)
        except Exception:
            time.sleep(1.5 ** a)
    raise RuntimeError("api failed: " + path)


def img_bytes(url, tries=4):
    for a in range(tries):
        try:
            r = S.get(url, timeout=60)
            if r.status_code == 200:
                return r.content
            time.sleep(1.5 ** a)
        except Exception:
            time.sleep(1.5 ** a)
    raise RuntimeError("img failed: " + url)


def basename_of(url):
    return url.split("?")[0].rsplit("/", 1)[-1].rsplit(".", 1)[0]


def shard_of(bn):
    h = bn[-5:-3] if len(bn) >= 7 else bn[:2]
    return re.sub(r"[^0-9a-zA-Z]", "_", h).ljust(2, "_")[:2].lower()


def load_ids(path):
    ids = set()
    if not os.path.exists(path):
        return ids
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            try:
                ids.add(int(json.loads(line)["id"]))
            except Exception:
                pass
    return ids


def append(path, rec):
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def record_len(path, sid):
    """Length of the LAST record for sid (build_data keeps the last one)."""
    n = None
    if not os.path.exists(path):
        return n
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            try:
                rec = json.loads(line)
            except Exception:
                continue
            if int(rec.get("id", -1)) == sid:
                n = len(rec.get("d") or [])
    return n


def one_char(cid):
    out = {"id": cid, "raw": None, "webp": None}
    raw = api("/v0/characters/%d" % cid)
    if not raw:
        return {"id": cid, "error": "no detail"}
    out["raw"] = raw
    img = (raw.get("images") or {}).get("medium")
    if img:
        bn = basename_of(img)
        sh = shard_of(bn)
        d = os.path.join(OUT_IMG, sh)
        dst = os.path.join(d, bn + ".webp")
        out["webp"] = "chars/%s/%s.webp" % (sh, bn)
        out["src_url"] = img
        if not os.path.exists(dst):
            blob = img_bytes(img)
            im = Image.open(io.BytesIO(blob)).convert("RGB")
            im.thumbnail((MAX_EDGE, MAX_EDGE), Image.LANCZOS)
            os.makedirs(d, exist_ok=True)
            tmp = dst + ".tmp%d" % os.getpid()
            im.save(tmp, "WEBP", quality=QUALITY, method=6)
            os.replace(tmp, dst)
        out["bytes"] = os.path.getsize(dst)
    return out


def main():
    t0 = time.time()
    subj_chars_p = os.path.join(TMP, "data", "subject_chars.jsonl")
    char_subj_p = os.path.join(TMP, "data", "char_subjects.jsonl")
    char_pers_p = os.path.join(TMP, "data", "char_persons.jsonl")
    chars_p = os.path.join(TMP, "chars_data.jsonl")

    known_subj = load_ids(subj_chars_p)
    known_chars = load_ids(chars_p)
    print("existing: subject_chars=%d chars_data=%d" % (len(known_subj), len(known_chars)), flush=True)

    todo = []
    for sid in SIDS:
        prev = record_len(subj_chars_p, int(sid))
        rows = api("/v0/subjects/%s/characters" % sid) or []
        append(subj_chars_p, {"id": int(sid), "d": rows})
        for r in rows:
            if r.get("relation") in ("主角", "配角"):
                todo.append(int(r["id"]))
        print("  %s: previous roster=%s -> refetched %d characters (%d 主角/配角)" % (
            sid, prev, len(rows),
            sum(1 for r in rows if r.get("relation") in ("主角", "配角"))), flush=True)

    missing = sorted({c for c in todo if c not in known_chars})
    print("characters needing new data: %d" % len(missing), flush=True)
    if not missing:
        print("nothing to do")
        return

    ok = err = 0
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(one_char, cid): cid for cid in missing}
        for i, fut in enumerate(as_completed(futs), 1):
            cid = futs[fut]
            r = fut.result()
            if r.get("error") or not r.get("webp"):
                err += 1
                print("    skip %s: %s" % (cid, r.get("error") or "no images.medium"), flush=True)
                continue
            append(chars_p, r)
            subs = api("/v0/characters/%d/subjects" % cid) or []
            append(char_subj_p, {"id": cid, "d": subs})
            pers = api("/v0/characters/%d/persons" % cid) or []
            append(char_pers_p, {"id": cid, "d": pers})
            ok += 1
            if i % 25 == 0:
                print("    %d/%d ok=%d err=%d %.0fs" % (i, len(missing), ok, err, time.time() - t0), flush=True)

    print("DONE ok=%d err=%d in %.0fs" % (ok, err, time.time() - t0), flush=True)


if __name__ == "__main__":
    main()
