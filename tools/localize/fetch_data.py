"""Phase 2: fetch all Bangumi data the game needs, for full local hosting.

Endpoints (from client/src/utils/bangumi.js):
  /v0/characters/{id}            -> already done in fetch_chars.py
  /v0/characters/{id}/subjects   -> appearance list      (getCharacterAppearances)
  /v0/characters/{id}/persons    -> voice actors         (animeVAs)
  /v0/subjects/{id}              -> subject details      (getSubjectDetails)
  /v0/subjects/{id}/characters   -> character roster     (getCharactersBySubjectId)

Outputs JSONL in OUT_DIR; resumable (skips ids already present).
"""
import urllib.request, json, re, os, sys, time, argparse, threading
from concurrent.futures import ThreadPoolExecutor, as_completed

_HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("ACG_REPO") or os.path.abspath(os.path.join(_HERE, "..", ".."))
WORK = os.environ.get("ACG_WORK") or os.path.join(_HERE, "_work")
os.makedirs(WORK, exist_ok=True)
ID_TAGS = os.path.join(REPO, "client", "src", "data", "id_tags.js")
OUT_DIR = os.path.join(WORK, "data")
UA = {"User-Agent": "anime-character-guessr/1.0 (https://github.com/BInBilibili/anime-character-guessr)"}
_lock = threading.Lock()


def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=45).read()


def char_ids():
    s = open(ID_TAGS, encoding="utf-8").read()
    return sorted({int(k) for k in re.findall(r"(?<![\d.])(\d+)\s*:\s*\[", s)})


def load_done(path):
    done = set()
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                try:
                    done.add(json.loads(line)["id"])
                except Exception:
                    pass
    return done


def fetch_many(ids, url_of, out_path, workers, label):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    done = load_done(out_path)
    todo = [i for i in ids if i not in done]
    print("[%s] total=%d already=%d todo=%d" % (label, len(ids), len(done), len(todo)), flush=True)
    if not todo:
        return done

    t0 = time.time()
    ok = err = 0
    errs = []
    with open(out_path, "a", encoding="utf-8") as fh, ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(_one, i, url_of(i)): i for i in todo}
        for n, fut in enumerate(as_completed(futs), 1):
            r = fut.result()
            with _lock:
                if r is None:
                    err += 1
                else:
                    ok += 1
                    fh.write(json.dumps(r, ensure_ascii=False) + "\n")
            if n % 500 == 0 or n == len(todo):
                el = time.time() - t0
                print("  [%s] %6d/%d ok=%d err=%d %.0fs (%.1f/s)"
                      % (label, n, len(todo), ok, err, el, n / max(el, .001)), flush=True)
    print("[%s] DONE ok=%d err=%d in %.0fs" % (label, ok, err, time.time() - t0), flush=True)
    return done


def _one(i, url):
    try:
        d = json.loads(get(url))
        return {"id": i, "d": d}
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=24)
    ap.add_argument("--phase", choices=["chars", "subjects", "all"], default="all")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    os.makedirs(OUT_DIR, exist_ok=True)
    ids = char_ids()
    if args.limit:
        ids = ids[: args.limit]

    if args.phase in ("chars", "all"):
        fetch_many(ids, lambda i: "https://api.bgm.tv/v0/characters/%d/subjects" % i,
                   os.path.join(OUT_DIR, "char_subjects.jsonl"), args.workers, "char/subjects")
        fetch_many(ids, lambda i: "https://api.bgm.tv/v0/characters/%d/persons" % i,
                   os.path.join(OUT_DIR, "char_persons.jsonl"), args.workers, "char/persons")

    # collect every subject id seen in char_subjects and (later) subject rosters
    subj_path = os.path.join(OUT_DIR, "char_subjects.jsonl")
    subj_ids = set()
    if os.path.exists(subj_path):
        with open(subj_path, encoding="utf-8") as fh:
            for line in fh:
                try:
                    for x in json.loads(line)["d"]:
                        if x.get("id"):
                            subj_ids.add(int(x["id"]))
                except Exception:
                    pass
    print("[subjects] distinct subject ids collected: %d" % len(subj_ids), flush=True)

    if args.phase in ("subjects", "all") and subj_ids:
        sids = sorted(subj_ids)
        fetch_many(sids, lambda i: "https://api.bgm.tv/v0/subjects/%d" % i,
                   os.path.join(OUT_DIR, "subjects.jsonl"), args.workers, "subject/detail")
        fetch_many(sids, lambda i: "https://api.bgm.tv/v0/subjects/%d/characters" % i,
                   os.path.join(OUT_DIR, "subject_chars.jsonl"), args.workers, "subject/chars")

    print("ALL DONE", flush=True)


if __name__ == "__main__":
    main()
