"""One-off: merge English overlay files (collections/_*/en/, pages/en/) into their Greek files.

usage: python3 -I merge_bilingual.py SITE_ROOT
"""
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from bilingual_yaml import LANG_FIELDS, clean, read, write  # noqa: E402

ROOT = sys.argv[1]
os.chdir(ROOT)

# old explicit English URLs that differ from the collection's permalink_en pattern
KEEP_EN_PERMALINK = {"programs", "staff_groups", "news_categories"}
PAIR_BY_KEY = {"sectors", "staff_groups", "news_categories", "programs"}
EN_RENAME = {"author_en": "author", "title_en": "title", "supervisor_en": "supervisor"}


def split(fm, body, lang):
    shared, block = {}, {}
    for k, v in fm.items():
        if k in ("lang", "ref", "translation"):
            continue
        if k in LANG_FIELDS:
            block[k] = v
        else:
            shared[k] = v
    if body.strip():
        block["body"] = body.strip() + "\n"
    return shared, block


def collections():
    n = 0
    for cdir in sorted(glob.glob("collections/_*")):
        name = cdir.split("/_", 1)[1]
        if name == "languages":
            continue
        greek = {os.path.basename(f)[:-3]: f for f in glob.glob(f"{cdir}/*.md")}
        merged = {}
        for f, path in greek.items():
            fm, body = read(path)
            if "el" in fm or "en" in fm:  # already converted
                merged[f] = (fm, None)
                continue
            if name == "links":
                fm = dict(fm)
                en_title = fm.pop("title_en", None)
                shared, el = split(fm, body, "el")
                merged[f] = ({**shared, "el": el, **({"en": {"title": en_title}} if en_title else {})}, None)
                continue
            shared, el = split(fm, body, "el")
            merged[f] = ({**shared, "el": el}, None)
        for path in sorted(glob.glob(f"{cdir}/en/*.md")):
            fm, body = read(path)
            fm = {EN_RENAME.get(k, k): v for k, v in fm.items()}
            base = os.path.basename(path)[:-3]
            target = None
            if name in PAIR_BY_KEY and fm.get("key"):
                target = next((g for g, (gfm, _) in merged.items() if gfm.get("key") == fm["key"]), None)
            if not target:
                ref = fm.get("ref") or base
                target = next((g for g in merged if g == ref or g.endswith("-" + ref) or g == base), None)
            permalink = fm.pop("permalink", None)
            _, en = split(fm, body, "en")
            if name in KEEP_EN_PERMALINK:
                en["permalink"] = permalink or f"/en/{'studies' if name == 'programs' else 'people'}/{base}/"
            elif permalink:
                en["permalink"] = permalink
            if target:
                gfm = merged[target][0]
                if fm.get("generated"):
                    gfm["generated"] = True
                gfm["en"] = {**gfm.get("en", {}), **en}
            else:  # English-only item
                shared, en2 = split({k: v for k, v in fm.items() if k not in LANG_FIELDS}, "", "en")
                merged[base] = ({**shared, "en": {**en}}, None)
            os.remove(path)
            n += 1
        for f, (fm, _) in merged.items():
            out = f"{cdir}/{f}.md"
            # keep shared keys first, then el, then en
            ordered = {k: v for k, v in fm.items() if k not in ("el", "en", "generated")}
            for lang in ("el", "en"):
                if fm.get(lang):
                    ordered[lang] = fm[lang]
            if fm.get("generated"):
                ordered["generated"] = True
            write(out, clean(ordered))
        if os.path.isdir(f"{cdir}/en") and not os.listdir(f"{cdir}/en"):
            os.rmdir(f"{cdir}/en")
    return n


def page_url(fm, path):
    if fm.get("permalink"):
        return fm["permalink"]
    if path == "index.html":
        return "/"
    return None


def pages():
    greek = {}
    files = ["index.html", "search.json"] + [p for p in glob.glob("pages/**/*.*", recursive=True) if not p.startswith("pages/en/")]
    for p in files:
        fm, body = read(p)
        if "el" in fm or "en" in fm:
            continue
        greek[p] = (fm, body)
    by_url = {page_url(fm, p): p for p, (fm, _) in greek.items() if page_url(fm, p)}
    by_url["/search.json"] = "search.json"
    out = {p: [fm, body, None] for p, (fm, body) in greek.items()}
    n = 0
    for p in sorted(glob.glob("pages/en/**/*.*", recursive=True)):
        fm, body = read(p)
        key = fm.get("translation") or ("/search.json" if p.endswith("search.json") else None)
        target = by_url.get(key) if key else None
        if target:
            out[target][2] = (fm, body)
            os.remove(p)
            n += 1
        else:
            out[p] = [{}, "", (fm, body)]  # English-only page: stays where it is
    for p, (gfm, gbody, en) in out.items():
        shared, el = split(gfm, "", "el")
        if gfm.get("permalink") or p == "index.html":
            el["permalink"] = gfm.get("permalink", "/")
        shared.pop("permalink", None)
        en_block = {}
        file_body = gbody
        if en:
            efm, ebody = en
            eshared, en_block = split(efm, "", "en")
            en_block["permalink"] = efm.get("permalink")
            for k, v in eshared.items():  # shared fields only present on the English page
                if k != "permalink":
                    shared.setdefault(k, v)
            if ebody.strip() != gbody.strip():
                if gbody.strip():
                    el["body"] = gbody.strip() + "\n"
                en_block["body"] = ebody.strip() + "\n"
                file_body = ""
        if not en and gbody.strip():  # Greek-only page: body belongs to the Greek block
            el["body"] = gbody.strip() + "\n"
            file_body = ""
        if not gfm:  # English-only
            el = {}
        fm = {k: v for k, v in shared.items() if k != "generated"}
        if el:
            fm["el"] = el
        if en_block:
            fm["en"] = en_block
        if shared.get("generated"):
            fm["generated"] = True
        write(p, clean(fm), file_body)
    for d in sorted(glob.glob("pages/en/**/", recursive=True), reverse=True):
        if os.path.isdir(d) and not os.listdir(d):
            os.rmdir(d)
    return n


if __name__ == "__main__":
    print("collection overlays merged:", collections())
    print("pages merged:", pages())
