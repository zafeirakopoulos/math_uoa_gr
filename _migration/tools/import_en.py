"""Import en.math.uoa.gr into English overlays/pages. Run AFTER import_site.py.

usage: python3 -I tools/import_en.py CRAWL_EN_DIR SITE_ROOT [--overwrite]
Safe by default: existing en: blocks and files are kept; --overwrite replaces them.

Adds an `en:` block to the Greek file of each item (one file per item, see
_plugins/bilingual.rb). Items that exist only in English get files with just an en: block.
"""
import difflib
import glob
import json
import os
import re
import sys
from urllib.parse import unquote, urlparse

import yaml
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.dirname(__file__))
from htmlmd import slugify, to_markdown  # noqa: E402
import bilingual_yaml as by  # noqa: E402

CRAWL, ROOT = sys.argv[1], sys.argv[2]
OVERWRITE = "--overwrite" in sys.argv[3:]
LEGACY = "https://en.math.uoa.gr"
RECS = {r["path"]: r for r in (json.load(open(f)) for f in glob.glob(os.path.join(CRAWL, "*.json")))}
REPORT = []

# old English path → new URL
FIXED = {
    "/": "/en/",
    "/the_department": "/en/the-department/",
    "/the_department/history": "/en/the-department/history/",
    "/the_department/organization_and_administration": "/en/the-department/administration/",
    "/the_department/organization_and_administration/department_administration": "/en/the-department/department-administration/",
    "/the_department/organization_and_administration/sections": "/en/sectors/",
    "/the_department/contact": "/en/contact/",
    "/the_department/contact/access": "/en/the-department/access/",
    "/undergraduate_studies": "/en/studies/undergraduate/",
    "/undergraduate_studies/courses": "/en/studies/undergraduate/courses/",
    "/undergraduate_studies/curriculum": "/en/studies/undergraduate/curriculum/",
    "/graduate_studies": "/en/studies/graduate/",
    "/doctoral_studies": "/en/studies/doctoral/",
    "/doctoral_studies/phd_candidates": "/en/studies/doctoral/phd-candidates/",
    "/conferences_seminars": "/en/seminars/",
    "/news_and_events": "/en/news/",
    "/news_and_events/news": "/en/news/general/",
    "/news_and_events/events": "/en/news/events/",
    "/news_and_events/top_picks": "/en/news/",
    "/people": "/en/people/",
    "/people/faculty": "/en/people/faculty/",
    "/people/faculty/alphabetically": "/en/people/faculty/",
    "/people/faculty/retired_faculty_members": "/en/people/retired-faculty/",
    "/people/special_teaching_staff": "/en/people/special-teaching-staff/",
    "/people/special_technical_and_scientific_staff": "/en/people/special-technical-staff/",
    "/people/administrative_staff": "/en/people/administrative-staff/",
    "/people/adjunct_faculty": "/en/people/adjunct-faculty/",
}
SECTOR_PAGES = {
    "/people/faculty/sector_of_algebra_and_geometry": "algebra-geometria",
    "/people/faculty/sector_of_mathematical_analysis": "analysi",
    "/people/faculty/sector_of_statistics_and_operation_research": "statistiki",
    "/people/faculty/sector_of_mathematics_education": "didaktiki",
    "/people/faculty/sector_of_applied_and_computational_mathematics": "efarmosmena",
}
for p, k in SECTOR_PAGES.items():
    FIXED[p] = f"/en/sectors/{k}/"


def link(href):
    href = href.strip()
    u = urlparse(href)
    if u.netloc and u.netloc not in ("en.math.uoa.gr",):
        return href
    if u.scheme in ("mailto", "tel"):
        return href
    path = unquote(u.path).rstrip("/") or "/"
    if path.startswith(("/fileadmin", "/typo3")):
        return LEGACY + u.path
    if path in FIXED:
        return FIXED[path]
    REPORT.append(f"unmapped EN link: {href}")
    return LEGACY + path


def set_en(relpath, en, body=""):
    """Add/replace the en: block of an existing (Greek) file."""
    path = os.path.join(ROOT, relpath)
    fm, file_body = by.read(path)
    if fm.get("en") and not OVERWRITE:
        REPORT.append(f"kept existing en: block in {relpath}")
        return
    en = by.clean(en)
    if body.strip():
        en["body"] = body.strip() + "\n"
    fm.pop("generated", None)
    fm["en"] = en
    fm["generated"] = True
    by.write(path, fm, file_body)


def write_en_only(relpath, shared, en, body=""):
    """A file that exists only in English."""
    if os.path.exists(os.path.join(ROOT, relpath)) and not OVERWRITE:
        REPORT.append(f"kept existing file: {relpath}")
        return
    en = by.clean(en)
    if body.strip():
        en["body"] = body.strip() + "\n"
    by.write(os.path.join(ROOT, relpath), {**by.clean(shared), "en": en, "generated": True})


def clean_generated():
    """Delete generated English-only files; en: blocks in Greek files are simply overwritten."""
    n = 0
    for f in glob.glob(os.path.join(ROOT, "collections/_*/*.md")) + glob.glob(os.path.join(ROOT, "pages/**/*.md"), recursive=True):
        fm, _ = by.read(f)
        if fm.get("generated") and fm.get("en") and not fm.get("el"):
            os.remove(f)
            n += 1
    return n


def md(path):
    return to_markdown(RECS[path]["content"], link)


def front(path):
    """Greek view of a collection doc: shared fields + el: block."""
    fm, _ = by.read(path)
    return {**{k: v for k, v in fm.items() if k not in ("el", "en")}, **(fm.get("el") or {})}


# ------------------------------------------------------------------ people matching
GREEK = {}
for f in glob.glob(os.path.join(ROOT, "collections/_people/*.md")):
    fm = front(f)
    GREEK[os.path.basename(f)[:-3]] = fm


# English forms of Greek first names, as used on en.math.uoa.gr
ALIASES = {"john": "ioannis", "yannis": "ioannis", "giannis": "ioannis", "george": "georgios", "lefteris": "elevtherios",
           "eleftherios": "elevtherios", "sophocles": "sofoklis", "nicholas": "nikolaos", "nick": "nikolaos",
           "michael": "michail", "demetris": "dimitrios", "demetrios": "dimitrios", "thanassis": "athanasios",
           "thanasis": "athanasios", "constantinos": "konstantinos", "costas": "konstantinos", "irene": "eirini",
           "theophilos": "theofilos", "stathis": "efstathios", "vassilis": "vasileios", "vasilis": "vasileios",
           "evangelos": "evaggelos", "panayiotis": "panagiotis", "gerassimos": "gerasimos", "stelios": "stylianos"}


def name_key(name):
    toks = re.findall(r"[a-z]+", slugify(name).replace("-", " "))
    return " ".join(sorted(ALIASES.get(t, t) for t in toks))


def tok_score(a, b):
    """Symmetric token alignment score between two transliterated names (order-independent)."""
    ta = [t for t in name_key(a).split() if len(t) > 1]
    tb = [t for t in name_key(b).split() if len(t) > 1]
    if not ta or not tb:
        return 0.0
    r = lambda x, y: difflib.SequenceMatcher(None, x, y).ratio()
    ab = sum(max(r(x, y) for y in tb) for x in ta) / len(ta)
    ba = sum(max(r(y, x) for x in ta) for y in tb) / len(tb)
    return (ab + ba) / 2


def match_person(rec, group_hint=None):
    em = rec.get("email")
    if em and not em.startswith("secr@"):
        hits = [k for k, v in GREEK.items() if v.get("email", "").lower() == em.lower()]
        if len(hits) == 1:
            return hits[0]
    for hint in ([group_hint, None] if group_hint else [None]):
        best, score = None, 0.0
        for k, v in GREEK.items():
            if hint and v.get("group") != hint:
                continue
            sc = tok_score(rec["title"], v["title"])
            if sc > score:
                best, score = k, sc
        if score >= 0.8:
            return best
    return None


EN_EMAIL = re.compile(r"([A-Za-z0-9._%+-]+)\s*(?:[\[\(]\s*(?:AT|at)\s*[\]\)]|@)\s*([A-Za-z0-9.-]+\.[a-z]{2,})")
RANK_EN = re.compile(r"(Professor Emeritus|Emeritus Professor|Associate Professor|Assistant Professor|Professor|Lecturer)")


def en_blocks(html):
    s = BeautifulSoup(re.sub(r"</strong>\s*<strong>", "", html), "html.parser")
    root = s.select_one(".single_page--content") or s
    for br in root.find_all("br"):
        br.replace_with("\n")
    for p in root.find_all(["p", "h2", "h3", "li"]):
        p.insert_after("\n")
    for a in root.find_all("a"):
        a.replace_with(a.get_text())
    return [c for c in root.get_text().replace("\xa0", " ").split("►")[1:]]


def parse_en(chunk):
    lines = [l.strip(" ,*") for l in chunk.split("\n") if l.strip(" ,*")]
    if not lines:
        return None
    flat = " ".join(lines)
    name = re.split(r",|Office|Sector:|Research|Administrative Secretary", lines[0])[0].strip(" ,.*")
    if "," in lines[0] and re.match(r"^[A-Z][a-z]+,\s*[A-Z]", lines[0]):  # "Surname, Firstname"
        parts = [x.strip() for x in lines[0].split(",")]
        name = f"{parts[0]} {parts[1]}"
    name = re.sub(r"([a-z])([A-Z][a-z])", r"\1 \2", name).strip()
    rec = {"title": re.sub(r"\s+", " ", name)}
    em = EN_EMAIL.search(flat)
    if em:
        rec["email"] = f"{em.group(1)}@{em.group(2)}"
    rk = RANK_EN.search(" ".join(lines[:2]))
    if rk:
        rec["rank_display"] = rk.group(1)
    ri = re.search(r"Research Interests\s*:?\s*(.*?)(?:Office|Sector|$)", flat)
    if ri and ri.group(1).strip(" :.*"):
        rec["interests"] = ri.group(1).strip(" :*").rstrip(".") + "."
    if "Administrative Secretary" in flat:
        rec["duties"] = "Head of the Secretariat"
    return rec


def import_people():
    n = 0
    seen = set()
    sources = [
        ("/people/faculty/alphabetically", "dep"),
        ("/people/special_teaching_staff", "edip"),
        ("/people/special_technical_and_scientific_staff", "etep"),
        ("/people/administrative_staff", "admin"),
        ("/people/adjunct_faculty", "teaching"),
    ]
    for path, group in sources:
        if path not in RECS:
            continue
        for chunk in en_blocks(RECS[path]["content"]):
            rec = parse_en(chunk)
            if not rec or len(rec["title"]) < 4:
                continue
            key = match_person(rec, group)
            if not key:
                REPORT.append(f"EN person not matched ({group}): {rec['title']}")
                continue
            if key in seen:
                continue
            seen.add(key)
            set_en(f"collections/_people/{key}.md", {k: rec.get(k) for k in ("title", "rank_display", "interests", "duties")})
            n += 1
    # retired: "Surname, Firstname X, Professor Emeritus (MA)"
    if "/people/faculty/retired_faculty_members" in RECS:
        s = BeautifulSoup(RECS["/people/faculty/retired_faculty_members"]["content"], "html.parser")
        text = s.get_text(" ")
        for chunk in text.split("►"):
            m = re.match(r"\s*([^,]+),\s*([^,]+?)\s*,\s*([^()]+?)\s*\(", chunk)
            if not m:
                continue
            rec = {"title": f"{m.group(1).strip()} {m.group(2).strip()}", "rank_display": m.group(3).strip()}
            key = match_person(rec, "retired")
            if key and key not in seen:
                seen.add(key)
                set_en(f"collections/_people/{key}.md", {"title": rec["title"], "rank_display": rec["rank_display"]})
                n += 1
            elif not key:
                REPORT.append(f"EN retired not matched: {rec['title']}")
    missing = [k for k, v in GREEK.items() if k not in seen]
    REPORT.append(f"{len(missing)} Greek people have no English overlay (fall back to Greek): " + ", ".join(sorted(missing)))
    return n


# ------------------------------------------------------------------ PhD candidates (overlays on theses)
def import_candidates():
    path = "/doctoral_studies/phd_candidates"
    if path not in RECS:
        return 0
    greek = {}
    for f in glob.glob(os.path.join(ROOT, "collections/_theses/candidate-*.md")):
        greek[os.path.basename(f)[:-3]] = front(f)
    s = BeautifulSoup(RECS[path]["content"], "html.parser")
    root = s.select_one(".single_page--content") or s
    n = 0
    for p in root.find_all("p"):
        for br in p.find_all("br"):
            br.replace_with("\n")
        lines = [l.strip(" ()\xa0") for l in p.get_text().split("\n") if l.strip(" ()\xa0")]
        if len(lines) < 2:
            continue
        sup = next((l for l in lines if l.startswith(("Advisor", "Supervisor"))), "")
        topic = next((l for l in lines[1:] if not l.startswith(("Advisor", "Supervisor"))), "")
        best, score = None, 0.0
        for k, v in greek.items():
            sc = tok_score(lines[0], v["author"])
            if sc > score:
                best, score = k, sc
        if not best or score < 0.8:
            REPORT.append(f"EN PhD candidate not matched: {lines[0]}")
            continue
        set_en(f"collections/_theses/{best}.md", {"author": lines[0], "title": topic,
                                                  "supervisor": re.sub(r"^(Advisor|Supervisor)s?\s*:?\s*", "", sup)})
        n += 1
    return n


# ------------------------------------------------------------------ simple overlays
SEMINARS_EN = {
    "geometrikis-theorias-anaparastaseon": "Geometric Representation Theory Seminar",
    "elliniko-mathimatiko-seminario": "Greek Mathematical Seminar",
    "statistikis-epicheirisiakis-erevnas": "Statistics & Operations Research Seminar",
    "arithmitikis-algevrikis-geometrias": "Arithmetic Algebraic Geometry Seminar",
    "efarmosmenis-analysis-merikon-diaforikon-exisoseon": "Applied Analysis & Partial Differential Equations Seminar",
    "geniko-seminario-tmimatos-mathimatikon-ekpa": "NKUA Mathematics Colloquium",
    "synartisiakis-analysis-kai-algevron-teleston": "Functional Analysis and Operator Algebras Seminar",
}


def import_overlays():
    n = 0
    for f in glob.glob(os.path.join(ROOT, "collections/_seminars/*.md")):
        key = os.path.basename(f)[:-3]
        if key in SEMINARS_EN:
            set_en(f"collections/_seminars/{key}.md", {"title": SEMINARS_EN[key]})
            n += 1
    return n


# ------------------------------------------------------------------ programmes, news, pages
def import_programs():
    progs = [("/undergraduate_studies", "undergraduate", "proptychiakes", "Undergraduate Studies", 1),
             ("/graduate_studies", "graduate", "metaptychiakes", "Graduate Studies", 2),
             ("/doctoral_studies", "doctoral", "didaktorikes", "Doctoral Studies", 3)]
    for path, fname, key, title, order in progs:
        if path in RECS:
            set_en(f"collections/_programs/{key}.md", {"title": title, "permalink": f"/en/studies/{fname}/",
                                                       "legacy_url": path}, md(path))
    for path, slug, title in [("/undergraduate_studies/courses", "courses", "Courses"),
                              ("/undergraduate_studies/curriculum", "curriculum", "Curriculum")]:
        if path in RECS:
            write_en_only(f"pages/en/studies/undergraduate-{slug}.md", {"section": "spoudes"}, {
                "title": title, "permalink": f"/en/studies/undergraduate/{slug}/", "parent_url": "/en/studies/undergraduate/",
                "parent_title": "Undergraduate Studies", "legacy_url": path}, md(path))


def import_news():
    n = 0
    for r in RECS.values():
        if r["kind"] != "news":
            continue
        s = BeautifulSoup(r["content"], "html.parser")
        t = s.select_one("#sysfolder_pid") or s.select_one(".single_page--title")
        title = re.sub(r"\s+", " ", t.get_text(" ", strip=True)) if t else r["head_title"]
        body = s.select(".single_page--content")
        body = body[-1] if body else s
        for x in body.select(".news-related-wrap"):
            x.decompose()
        d = r.get("date") or "2026-01-01"
        slug = slugify(r["path"].rsplit("/", 1)[1].replace("_", " "), 60)
        cat = "ekdiloseis" if "/view_event/" in r["path"] else "genikes"
        summary = re.sub(r"\s+", " ", body.get_text(" ", strip=True))[:220]
        write_en_only(f"collections/_news/{d}-{slug}.md", {"date": d, "categories": [cat]},
                      {"title": title, "summary": summary, "legacy_url": r["path"]}, to_markdown(str(body), link))
        n += 1
    return n


# English page → (Greek page file it translates, new URL, title, nav title)
PAGES = {
    "/the_department/history": ("pages/to-tmima/istoria.md", "/en/the-department/history/", "History", None),
    "/the_department/organization_and_administration": ("pages/to-tmima/dioikisi.md", "/en/the-department/administration/", "Organisation and Administration", "Administration"),
    "/the_department/organization_and_administration/department_administration": ("pages/to-tmima/dioikitiki-diarthrosi.md", "/en/the-department/department-administration/", "Department Administration", None),
    "/the_department/contact/access": ("pages/to-tmima/prosvasi.md", "/en/the-department/access/", "Access", None),
}


def import_pages():
    for old, (greek_file, permalink, title, nav_title) in PAGES.items():
        if old not in RECS:
            REPORT.append(f"EN page missing: {old}")
            continue
        if not os.path.exists(os.path.join(ROOT, greek_file)):
            REPORT.append(f"Greek page for {old} not found: {greek_file}")
            continue
        set_en(greek_file, {"title": title, "nav_title": nav_title, "permalink": permalink, "legacy_url": old}, md(old))


def sector_ledes():
    """Official English area lists from /the_department/organization_and_administration/sections."""
    path = "/the_department/organization_and_administration/sections"
    out = {}
    if path in RECS:
        items = BeautifulSoup(RECS[path]["content"], "html.parser").find_all("li")
        keys = ["algebra-geometria", "analysi", "statistiki", "didaktiki", "efarmosmena"]
        for k, li in zip(keys, items):
            out[k] = re.sub(r"\s+", " ", li.get_text(" ", strip=True).split(":", 1)[1]).strip()
    return out


if __name__ == "__main__":
    if OVERWRITE:
        print("removed stale EN files:", clean_generated())
    print("people", import_people())
    print("phd candidates", import_candidates())
    print("overlays", import_overlays())
    import_programs()
    print("news", import_news())
    import_pages()
    ledes = sector_ledes()
    with open(os.path.join(ROOT, "_migration/sector-ledes-en.json"), "w") as f:
        json.dump(ledes, f, ensure_ascii=False, indent=1)
    with open(os.path.join(ROOT, "_migration/import-report-en.txt"), "w") as f:
        f.write("\n".join(REPORT) + "\n")
    print(len(REPORT), "report lines")
