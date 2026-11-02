"""Turn the crawl of www.math.uoa.gr into Jekyll collections + pages.

usage: python3 -I tools/import_site.py CRAWL_DIR SITE_ROOT [--overwrite]
Safe by default: existing files are never touched (only missing ones are created).
With --overwrite, files marked `generated: true` are deleted and regenerated
(their en: blocks are kept); hand edits in those files are lost.
"""
import glob
import json
import os
import re
import sys
from datetime import date
from urllib.parse import unquote, urlparse

import yaml
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.dirname(__file__))
from htmlmd import slugify, to_markdown  # noqa: E402
from people import parse_people, parse_block, sector_key, norm_rank, FEMALE_RANK  # noqa: E402
import bilingual_yaml as by  # noqa: E402

CRAWL, ROOT = sys.argv[1], sys.argv[2]
OVERWRITE = "--overwrite" in sys.argv[3:]
LEGACY = "https://www.math.uoa.gr"
RECS = {r["path"]: r for r in (json.load(open(f)) for f in glob.glob(os.path.join(CRAWL, "*.json")))}
REPORT = []

# ------------------------------------------------------------------ URL map (old → new)
# old path: (new permalink, section, nav_order, title override, nav_title)
PAGES = {
    "/to_tmima": ("/to-tmima/", "to-tmima", None, "Το Τμήμα", None),
    "/to_tmima/istorika_stoicheia": ("/to-tmima/istoria/", "to-tmima", 1, "Ιστορικά στοιχεία", "Ιστορία"),
    "/to_tmima/dioikitiki_organosi": ("/to-tmima/dioikisi/", "to-tmima", 3, "Διοικητική οργάνωση", "Διοίκηση"),
    "/to_tmima/dioikitiki_organosi/dioikitiki_diarthrosi": ("/to-tmima/dioikitiki-diarthrosi/", "to-tmima", 4, "Διοικητική διάρθρωση", None),
    "/to_tmima/prosbasi_egkatastaseis": ("/to-tmima/prosvasi/", "to-tmima", 7, "Πρόσβαση", None),
    "/to_tmima/prosbasi_egkatastaseis/ktiriakes_egkatastaseis": ("/to-tmima/egkatastaseis/", "to-tmima", 8, "Κτιριακές εγκαταστάσεις", "Εγκαταστάσεις"),
    "/to_tmima/kodika_deontologias_kai_kalis_praktikis": ("/to-tmima/kodikas-deontologias/", "to-tmima", 9, "Κώδικας δεοντολογίας και καλής πρακτικής", "Κώδικας δεοντολογίας"),
    "/to_tmima/pistopoiisi_proptychiakoy_programmatos_spoydon": ("/to-tmima/pistopoiisi/", "to-tmima", 10, "Πιστοποίηση Προπτυχιακού Προγράμματος Σπουδών", "Πιστοποίηση ΠΠΣ"),
    "/mitroo_eklektoron_tmimatos": ("/to-tmima/mitroo-eklektoron/", "to-tmima", 11, "Μητρώο εκλεκτόρων", None),
    "/proptychiakes_spoydes/eggrafes_protoeton_foititon": ("/spoudes/eggrafes-protoeton/", "spoudes", 4, "Εγγραφές πρωτοετών φοιτητών", "Εγγραφές πρωτοετών"),
    "/proptychiakes_spoydes/katataktiries_exetaseis_2024_25": ("/spoudes/katataktiries/", "spoudes", 5, None, "Κατατακτήριες εξετάσεις"),
    "/proptychiakes_spoydes/katataktiries_exetaseis_2024_25_2": ("/spoudes/katataktiries-2025-26/", "spoudes", None, None, None),
    "/proptychiakes_spoydes/meriki_foitisi": ("/spoudes/meriki-foitisi/", "spoudes", 6, "Μερική φοίτηση", None),
    "/proptychiakes_spoydes/metafora_theseon_foitisis_stelechon_enoplon_dynameon_kai_somaton_asfaleias": ("/spoudes/metafora-theseon-enoplon-dynameon/", "spoudes", None, None, None),
    "/proptychiakes_spoydes/mathimata_allon_tmimaton_2024_25": ("/spoudes/mathimata-allon-tmimaton/", "spoudes", 7, None, "Μαθήματα άλλων Τμημάτων"),
    "/proptychiakes_spoydes_2": ("/spoudes/akadimaiko-etos-2025-26/", "spoudes", None, None, None),
    "/proptychiakes_spoydes_1": ("/spoudes/archeio/2024-25/", "spoudes", None, None, None),
    "/proptychiakes_spoydes/archeio_proigoymenon_eton": ("/spoudes/archeio/", "spoudes", 12, "Αρχείο προηγούμενων ετών", "Αρχείο ετών"),
    "/katataktiries_exetaseis": ("/spoudes/archeio/katataktiries-2019-20/", "spoudes", None, None, None),
    "/praktiki_askisi_foititon": ("/spoudes/praktiki-askisi/", "spoudes", 8, "Πρακτική άσκηση φοιτητών", "Πρακτική άσκηση"),
    "/praktiki_askisi_foititon/diadikasia_epilogis": ("/spoudes/praktiki-askisi/diadikasia-epilogis/", "spoudes", None, "Πρακτική άσκηση: διαδικασία επιλογής", None),
    "/praktiki_askisi_foititon/formes_praktikis_askisis": ("/spoudes/praktiki-askisi/formes/", "spoudes", None, "Πρακτική άσκηση: φόρμες", None),
    "/metaptychiakes_spoydes/anakoinoseis_metaptychiakon_ektos_tmimatos": ("/spoudes/metaptychiakes/allon-tmimaton/", "spoudes", None, "Ανακοινώσεις μεταπτυχιακών (εκτός Τμήματος)", None),
    "/metaptychiakes_spoydes/anakoinoseis_metaptychiakon_ektos_tmimatos/pms_mathimatika/prokiryxi_pms_2022_23": ("/spoudes/metaptychiakes/prokiryxi-2022-23/", "spoudes", None, None, None),
}
# archive (year) pages: generated permalink
for p in RECS:
    if p.startswith("/proptychiakes_spoydes/archeio_proigoymenon_eton/") and p not in PAGES:
        tail = p.split("/archeio_proigoymenon_eton/")[1]
        PAGES[p] = ("/spoudes/archeio/" + "/".join(slugify(x.replace("_", " ")) for x in tail.split("/")) + "/", "spoudes", None, None, None)

PROGRAMS = {
    "/proptychiakes_spoydes": ("proptychiakes", "Προπτυχιακές σπουδές", 1, None, None),
    "/metaptychiakes_spoydes": ("metaptychiakes", "Μεταπτυχιακές σπουδές", 2, None, None),
    "/didaktorikes_spoydes": ("didaktorikes", "Διδακτορικές σπουδές", 3, None, None),
    "/metaptychiakes_spoydes/anakoinoseis_metaptychiakon_ektos_tmimatos/pms_mathimatika": ("pms-mathimatika", "ΠΜΣ «Μαθηματικά»", None, "metaptychiakes", None),
    "/metaptychiakes_spoydes/anakoinoseis_metaptychiakon_ektos_tmimatos/pms_mathimatika/theoritika_mathimatika": ("pms-theoritika-mathimatika", "ΠΜΣ Μαθηματικά — Θεωρητικά Μαθηματικά", None, "pms-mathimatika", "theoritika"),
    "/metaptychiakes_spoydes/anakoinoseis_metaptychiakon_ektos_tmimatos/pms_mathimatika/efarmosmena_mathimatika": ("pms-efarmosmena-mathimatika", "ΠΜΣ Μαθηματικά — Εφαρμοσμένα Μαθηματικά", None, "pms-mathimatika", "efarmosmena"),
    "/metaptychiakes_spoydes/anakoinoseis_metaptychiakon_ektos_tmimatos/pms_mathimatika/statistiki_kai_epicheirisiaki_ereyna": ("pms-statistiki", "ΠΜΣ Μαθηματικά — Στατιστική και Επιχειρησιακή Έρευνα", None, "pms-mathimatika", "statistiki"),
}

AWARD_PAGES = [p for p in RECS if p.startswith("/diakriseis_melon_tmimatos/")]
SECTOR_PAGES = {
    "/anthropino_dynamiko/meli_dep/tomeas_algebras_geometrias": "algebra-geometria",
    "/anthropino_dynamiko/meli_dep/tomeas_mathimatikis_analysis": "analysi",
    "/anthropino_dynamiko/meli_dep/tomeas_statistikis_kai_epicheirisiakis_ereynas": "statistiki",
    "/anthropino_dynamiko/meli_dep/tomeas_didaktikis_ton_mathimatikon": "didaktiki",
    "/anthropino_dynamiko/meli_dep/tomeas_efarmosmenon_kai_ypologistikon_mathimatikon": "efarmosmena",
}
FIXED = {
    "/": "/",
    "/anakoinoseis": "/anakoinoseis/",
    "/anakoinoseis_kai_ekdiloseis": "/anakoinoseis/",
    "/anakoinoseis_kai_ekdiloseis/anakoinoseis": "/anakoinoseis/genikes/",
    "/anakoinoseis_kai_ekdiloseis/prokiryxeis": "/anakoinoseis/prokiryxeis/",
    "/anakoinoseis_kai_ekdiloseis/ekdiloseis": "/anakoinoseis/ekdiloseis/",
    "/anakoinoseis_kai_ekdiloseis/epilegmena": "/anakoinoseis/",
    "/prokiryxeis_1": "/anakoinoseis/prokiryxeis/",
    "/anthropino_dynamiko": "/anthropino-dynamiko/",
    "/anthropino_dynamiko/meli_dep": "/anthropino-dynamiko/meli-dep/",
    "/anthropino_dynamiko/meli_dep/alfabitika": "/anthropino-dynamiko/meli-dep/",
    "/anthropino_dynamiko/meli_edip": "/anthropino-dynamiko/edip/",
    "/anthropino_dynamiko/meli_etep": "/anthropino-dynamiko/etep/",
    "/anthropino_dynamiko/dioikitiko_prosopiko": "/anthropino-dynamiko/dioikitiko/",
    "/anthropino_dynamiko/didaskontes": "/anthropino-dynamiko/didaskontes/",
    "/to_tmima/istorika_stoicheia/afypiretisanta_meli_dep": "/anthropino-dynamiko/afypiretisantes/",
    "/to_tmima/istorika_stoicheia/diatelesantes_proedroi_kai_an_proedroi_toy_tmimatos": "/to-tmima/proedroi/",
    "/didaktorikes_spoydes/didaktores_toy_tmimatos_mathimatikon": "/spoudes/didaktorikes/didaktores/",
    "/didaktorikes_spoydes/ypopsifioi_didaktores_toy_tmimatos_mathimatikon": "/spoudes/didaktorikes/ypopsifioi/",
    "/chrisima_entypa": "/spoudes/entypa/",
    "/chrisimoi_syndesmoi": "/spoudes/syndesmoi/",
    "/diakriseis_melon_tmimatos": "/diakriseis/",
    "/seminaria_synedria": "/seminaria/",
    "/to_tmima/ergastiria_i/y": "/ergastiria/ergastirio-ypologiston/",
}
for p in RECS:
    if p.startswith("/chrisima_entypa/"):
        FIXED[p] = "/spoudes/entypa/"
for p, s in SECTOR_PAGES.items():
    FIXED[p] = f"/tomeis/{s}/"
for p, v in PAGES.items():
    FIXED[p] = v[0]
for p, v in PROGRAMS.items():
    FIXED[p] = f"/spoudes/{v[0]}/"
for p in AWARD_PAGES:
    FIXED[p] = f"/diakriseis/{slugify(RECS[p]['head_title'])}/"
for p in RECS:
    if p.endswith(("diplomatikes_ergasies_efarmosmenon_mathimatikon", "diplomatikes_ergasies_statistikis_kai_epicheirisiakis_ereynas", "diplomatikes_ergasies_theoritikon_mathimatikon")):
        FIXED[p] = "/spoudes/metaptychiakes/diplomatikes/"

NEWS_URL = {}  # filled when news are written


def link(href):
    href = href.strip()
    u = urlparse(href)
    if u.netloc and u.netloc not in ("www.math.uoa.gr", "math.uoa.gr"):
        return href
    if u.scheme in ("mailto", "tel"):
        return href
    path = unquote(u.path).rstrip("/") or "/"
    if path.startswith(("/fileadmin", "/typo3")):
        return LEGACY + u.path  # TODO: files still served from the old host
    if path in FIXED:
        return FIXED[path]
    if path in NEWS_URL:
        return NEWS_URL[path]
    if "/proboli_anakoinosis/" in path or "/proboli_ekdilosis/" in path:
        slug = path.rsplit("/", 1)[1]
        for k, v in NEWS_URL.items():
            if k.endswith("/" + slug):
                return v
        return LEGACY + path
    REPORT.append(f"unmapped internal link: {href}")
    return LEGACY + path


# ------------------------------------------------------------------ writing
KEPT_EN = {}  # en: blocks of generated files, kept across re-imports (filled by clean_generated)


def write(relpath, fm, body=""):
    """Write a generated file in the one-file bilingual format: shared fields + el: block (+ kept en:)."""
    fm = by.clean(fm)
    el = {k: v for k, v in fm.items() if k in by.LANG_FIELDS or k == "permalink"}
    shared = {k: v for k, v in fm.items() if k not in el and k != "translation"}
    if body.strip():
        el["body"] = body.strip() + "\n"
    out = {**shared, "el": el}
    if KEPT_EN.get(relpath):
        out["en"] = KEPT_EN[relpath]
    out["generated"] = True
    path = os.path.join(ROOT, relpath)
    if os.path.exists(path) and not OVERWRITE:
        REPORT.append(f"kept existing file: {relpath}")
        return
    by.write(path, out)


def md_of(path, html=None):
    return to_markdown(html if html is not None else RECS[path]["content"], link)


def title_of(path):
    t = RECS[path]["head_title"].strip()
    return re.sub(r"\s+", " ", t)


# ------------------------------------------------------------------ news
NEWS_CATS = {"ΑΝΑΚΟΙΝΩΣΕΙΣ": "genikes", "ΠΡΟΚΗΡΥΞΕΙΣ": "prokiryxeis", "ΕΚΔΗΛΩΣΕΙΣ": "ekdiloseis",
             "ΣΕΜΙΝΑΡΙΑ": "seminaria", "ΜΕΤΑΠΤΥΧΙΑΚΑ": "metaptychiaka"}


def news_parts(rec):
    s = BeautifulSoup(rec["content"], "html.parser")
    t = s.select_one("#sysfolder_pid") or s.select_one(".single_page--title")
    title = re.sub(r"\s+", " ", t.get_text(" ", strip=True)) if t else rec["head_title"]
    cat = s.select_one(".page_category_title")
    cat = cat.get_text(strip=True) if cat else "ΑΝΑΚΟΙΝΩΣΕΙΣ"
    body = s.select(".single_page--content")
    body = body[-1] if body else s
    for x in body.select(".news-related-wrap"):
        # attachments live here
        pass
    atts = []
    for a in body.select(".news-related-wrap a[href]"):
        atts.append({"title": a.get_text(" ", strip=True) or a["href"].rsplit("/", 1)[-1], "url": link(a["href"])})
    for x in body.select(".news-related-wrap"):
        x.decompose()
    return title, cat, str(body), atts


def import_news():
    items = [r for r in RECS.values() if r["kind"] == "news"]
    seen, used = {}, set()
    for r in sorted(items, key=lambda r: (r.get("date") or "", r["path"])):
        if "proboli_anakoinosis" not in r["path"]:
            continue
        d = r.get("date") or "2026-01-01"
        slug = slugify(r["path"].rsplit("/", 1)[1].replace("_", " "), 60)
        base, i = slug, 2
        while (d[:4], slug) in used:
            slug, i = f"{base}-{i}", i + 1
        used.add((d[:4], slug))
        NEWS_URL[r["path"]] = f"/anakoinoseis/{d[:4]}/{d}-{slug}/"
        seen[r["path"]] = (d, slug)
    for r in items:
        if r["path"] not in seen:
            continue
        d, slug = seen[r["path"]]
        title, cat, html, atts = news_parts(r)
        body = to_markdown(html, link)
        summary = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
        summary = re.sub(r"https?://\S+", "", summary)
        summary = re.sub(r"\s+", " ", summary).strip()[:220]
        # fix the generated permalink: :name of a dated file excludes the date
        NEWS_URL[r["path"]] = f"/anakoinoseis/{d[:4]}/{slug}/"
        write(f"collections/_news/{d}-{slug}.md", {
            "title": title,
            "date": d,
            "categories": [NEWS_CATS.get(cat.upper(), "genikes")],
            "summary": summary,
            "attachments": atts,
            "legacy_url": r["path"],
        }, body)
    return len(seen)


# ------------------------------------------------------------------ people
def person_file(rec, group, extra=None):
    name = rec["title"].strip()
    fm = {"title": name, "sort_name": name, "group": group}
    for k in ("rank", "rank_display", "sector", "office", "phone", "email", "website", "interests", "field", "duties"):
        if rec.get(k):
            fm[k] = rec[k]
    if group == "admin" and len(name.split()) == 2:
        fm["sort_name"] = " ".join(reversed(name.split()))
    if extra:
        fm.update(extra)
    if fm.get("rank") and rec.get("rank_display") and re.search(r"(τρια|τρια|ούρη|κουρη|ήτρια|ητρια)", rec["rank_display"]):
        fm["rank_display"] = FEMALE_RANK.get(fm["rank"], rec["rank_display"])
    return fm


def import_people():
    people = {}
    # 1) ΔΕΠ from the sector pages (authoritative rank + sector)
    for path, sector in SECTOR_PAGES.items():
        html = RECS[path]["content"]
        parts = re.split(r"(<h2[^>]*>.*?</h2>)", html, flags=re.S)
        rank = None
        for part in parts:
            if part.startswith("<h2"):
                rank = norm_rank(BeautifulSoup(part, "html.parser").get_text())
                continue
            for p in parse_people(part):
                p["sector"] = sector
                if rank:
                    p["rank"] = rank
                people[slugify(p["title"])] = ("dep", p)
    # 2) enrich from the alphabetical list (websites, display ranks, interests)
    alpha = parse_people(RECS["/anthropino_dynamiko/meli_dep/alfabitika"]["content"])
    for a in alpha:
        key = slugify(a["title"])
        if key in people:
            g, p = people[key]
            for k in ("website", "rank_display", "phone", "office", "interests"):
                if a.get(k) and not p.get(k):
                    p[k] = a[k]
        else:
            REPORT.append(f"ΔΕΠ only in alphabetical list (check): {a['title']} — {a.get('rank_display')} {a.get('sector')}")
            people[key] = ("dep", a)
    # 3) other groups
    for path, group in [("/anthropino_dynamiko/meli_edip", "edip"), ("/anthropino_dynamiko/meli_etep", "etep"),
                        ("/anthropino_dynamiko/didaskontes", "teaching")]:
        for p in parse_people(RECS[path]["content"]):
            p.pop("rank", None)
            people[slugify(p["title"])] = (group, p)
    for p in parse_admin(RECS["/anthropino_dynamiko/dioikitiko_prosopiko"]["content"]):
        people[slugify(p["title"])] = ("admin", p)
    for p in parse_retired(RECS["/to_tmima/istorika_stoicheia/afypiretisanta_meli_dep"]["content"]):
        k = slugify(p["title"])
        if k not in people:
            people[k] = ("retired", p)
    for key, (group, p) in people.items():
        if len(p["title"].split()) < 2:
            REPORT.append(f"suspicious person name: {p['title']!r} ({group})")
        fm = person_file(p, group)
        if group == "dep" and p.get("rank_display"):
            fm["rank_display"] = p["rank_display"]
        # Χαλικιάς block on the old site swallowed the next entry — strip it
        if fm.get("interests"):
            fm["interests"] = re.sub(r"\.\s*[Α-Ω][α-ωά-ώ]+ [Α-Ω][α-ωά-ώ]+,.*$", ".", fm["interests"]).strip()
        write(f"collections/_people/{key}.md", fm, p.get("bio", ""))
    return people


def parse_admin(html):
    html = re.sub(r"</strong>\s*<strong>", "", html)
    s = BeautifulSoup(html, "html.parser")
    out, cur = [], None
    for p in s.find_all("p"):
        text = re.sub(r"\s+", " ", p.get_text(" ", strip=True)).replace("\xa0", " ")
        if not text:
            continue
        strong = p.find(["strong", "b"])
        lead = strong.get_text(" ", strip=True) if strong else ""
        if strong and not lead.startswith(("Γραφείο", "Τηλέφωνο", "e-mail")):
            name = re.split(r"[,:]", lead)[0].strip()
            if name.startswith("Γραμματέας"):
                name = re.sub(r"^Γραμματέας Τμήματος\s*:?\s*", "", lead).split("Γραφείο")[0].strip(" ,")
                duties = "Γραμματέας του Τμήματος"
            else:
                duties = text[len(lead):].split("Γραφείο")[0].strip(" ,.")
            rec = parse_block(text.replace(lead, name + "\n", 1)) or {}
            cur = {"title": re.sub(r"^K", "Κ", name), "duties": duties}
            for k in ("office", "phone", "email"):
                if rec.get(k):
                    cur[k] = rec[k]
            out.append(cur)
        elif cur is not None:
            rec = parse_block("x\n" + text) or {}
            for k in ("office", "phone", "email"):
                if rec.get(k) and not cur.get(k):
                    cur[k] = rec[k]
            if not cur.get("duties"):
                cur["duties"] = text.split("Γραφείο")[0].strip(" ,.")
    return out


RETIRED_SECTOR = {"ΜΑ": "analysi", "ΑΓ": "algebra-geometria", "ΔΜ": "didaktiki", "ΣΕΕ": "statistiki", "ΣΕ": "statistiki",
                  "ΕΥΜ": "efarmosmena", "ΕΜ": "efarmosmena"}


def parse_retired(html):
    s = BeautifulSoup(html, "html.parser")
    for a in s.find_all("a"):
        href = a.get("href", "")
        a.replace_with(f"{a.get_text()}⟦{href}⟧")
    text = s.get_text(" ")
    out = []
    for chunk in text.split("►"):
        sites = re.findall(r"⟦(.*?)⟧", chunk)
        c = re.sub(r"⟦.*?⟧", "", chunk).strip(" ,\n")
        m = re.match(r"\s*([^,]+?),\s*([^()]+?)\s*\(([^)]+)\)", c)
        if not m:
            continue
        rec = {"title": re.sub(r"\s+", " ", m.group(1)).strip(), "rank_display": m.group(2).strip()}
        sk = RETIRED_SECTOR.get(m.group(3).strip())
        if sk:
            rec["sector"] = sk
        if sites and sites[0].startswith("http"):
            rec["website"] = sites[0]
        out.append(rec)
    return out


# ------------------------------------------------------------------ theses (PhD)
def import_theses():
    n = 0
    # graduates
    s = BeautifulSoup(RECS["/didaktorikes_spoydes/didaktores_toy_tmimatos_mathimatikon"]["content"], "html.parser")
    root = s.select_one(".single_page--content") or s
    year = None
    for el in root.descendants:
        if getattr(el, "name", None) in ("p", "h2", "h3", "strong") and re.fullmatch(r"\s*(19|20)\d\d\s*", el.get_text()):
            year = int(el.get_text().strip())
        if getattr(el, "name", None) == "li" and year:
            a = el.find("a")
            for br in el.find_all("br"):
                br.replace_with("\n")
            lines = [l.strip(" \t<>\xa0") for l in el.get_text().split("\n") if l.strip(" \t<>\xa0")]
            if len(lines) < 2:
                continue
            sup = next((l for l in lines if l.startswith("Επιβλέπ")), "")
            title_line = next((l for l in lines[1:] if not l.startswith("Επιβλέπ")), "")
            fm = {"title": title_line, "author": lines[0], "year": year, "status": "completed",
                  "supervisor": re.sub(r"^Επιβλέπ\w*\s*:?\s*", "", sup), "link": a["href"] if a else None,
                  "legacy_url": "/didaktorikes_spoydes/didaktores_toy_tmimatos_mathimatikon"}
            write(f"collections/_theses/{year}-{slugify(lines[0], 40)}.md", fm)
            n += 1
    # candidates
    s = BeautifulSoup(RECS["/didaktorikes_spoydes/ypopsifioi_didaktores_toy_tmimatos_mathimatikon"]["content"], "html.parser")
    root = s.select_one(".single_page--content") or s
    sector = None
    for el in root.find_all(["h2", "p"]):
        if el.name == "h2":
            sector = sector_key(el.get_text())
            continue
        for br in el.find_all("br"):
            br.replace_with("\n")
        lines = [l.strip(" \t()\xa0") for l in el.get_text().split("\n") if l.strip(" \t()\xa0")]
        if len(lines) < 2:
            continue
        sup = next((l for l in lines if l.startswith("Επιβλέπ")), "")
        topic = next((l for l in lines[1:] if not l.startswith("Επιβλέπ")), "")
        fm = {"title": topic.rstrip("."), "author": lines[0], "status": "in-progress", "sector": sector,
              "supervisor": re.sub(r"^Επιβλέπ\w*\s*:?\s*", "", sup).strip(" )"),
              "legacy_url": "/didaktorikes_spoydes/ypopsifioi_didaktores_toy_tmimatos_mathimatikon"}
        write(f"collections/_theses/candidate-{slugify(lines[0], 40)}.md", fm)
        n += 1
    return n


# ------------------------------------------------------------------ forms
FORM_AUDIENCE = {
    "/chrisima_entypa/entypa_melon_dep": ("dep", "Μέλη ΔΕΠ"),
    "/chrisima_entypa/entypa_metaptychiakon": ("metaptychiakoi", "Μεταπτυχιακοί φοιτητές"),
    "/chrisima_entypa/entypa_proptychiakon_apofoiton": ("proptychiakoi", "Προπτυχιακοί φοιτητές & απόφοιτοι"),
    "/chrisima_entypa/entypa_ypopsifion_didaktoron": ("ypopsifioi", "Υποψήφιοι διδάκτορες"),
}


def import_forms():
    n = 0
    for path, (aud, _) in FORM_AUDIENCE.items():
        if path not in RECS:
            continue
        s = BeautifulSoup(RECS[path]["content"], "html.parser")
        root = s.select_one(".single_page--content") or s
        html = str(root)
        for i, chunk in enumerate(html.split("►")[1:], 1):
            cs = BeautifulSoup(chunk, "html.parser")
            files = [{"label": a.get_text(" ", strip=True), "url": link(a["href"])} for a in cs.find_all("a", href=True)]
            for a in cs.find_all("a"):
                a.decompose()
            title = re.sub(r"\s+", " ", cs.get_text(" ", strip=True)).strip(" ή,:-")
            if not title and files:
                title = files[0]["label"]
                files[0]["label"] = "Αρχείο"
            if not files or not title:
                continue
            for f in files:
                ext = f["url"].rsplit(".", 1)[-1].lower()
                f["format"] = ext if ext in ("pdf", "doc", "docx", "xls", "xlsx", "odt") else "link"
            write(f"collections/_forms/{aud}-{i:02d}-{slugify(title, 40)}.md",
                  {"title": title, "audience": aud, "order": i, "files": files, "legacy_url": path})
            n += 1
    return n


# ------------------------------------------------------------------ awards, seminars, conferences
def import_awards():
    for i, p in enumerate(sorted(AWARD_PAGES), 1):
        t = title_of(p)
        write(f"collections/_awards/{slugify(t)}.md", {"title": t, "order": i, "legacy_url": p}, md_of(p))
    # landing intro
    return len(AWARD_PAGES)


def import_seminars():
    s = BeautifulSoup(RECS["/seminaria_synedria"]["content"], "html.parser")
    root = s.select_one(".single_page--content") or s
    n = 0
    # seminar series: links between "Σεμινάρια" and "Συνέδρια"
    html = str(root)
    sem_part = html.split("Συνέδρια")[0]
    sem_part = sem_part.split("Σεμινάρια", 1)[-1]
    order = 0
    for a in BeautifulSoup(sem_part, "html.parser").find_all("a", href=True):
        t = re.sub(r"\s+", " ", a.get_text(" ", strip=True))
        if not t or "Θερινό Σχολείο" in t:
            continue
        order += 1
        key = slugify(re.sub(r"^Σεμινάριο\s+", "", t), 50)
        write(f"collections/_seminars/{key}.md", {"key": key, "title": t, "order": order, "website": link(a["href"]),
                                                    "sector": sector_for_seminar(t), "legacy_url": "/seminaria_synedria"})
        n += 1
    # conferences table → events
    table = root.find("table")
    ev = 0
    if table:
        for tr in table.find_all("tr"):
            tds = tr.find_all("td")
            if len(tds) < 2:
                continue
            when = tds[0].get_text(" ", strip=True)
            a = tds[1].find("a", href=True)
            t = re.sub(r"\s+", " ", a.get_text(" ", strip=True)) if a else tds[1].get_text(" ", strip=True)[:120]
            href = link(a["href"]) if a else None
            d = parse_greek_date(when)
            if not d or not t:
                REPORT.append(f"conference row not parsed: {when!r} {t[:60]!r}")
                continue
            for x in tds[1].find_all("a"):
                if x.get_text(" ", strip=True) == t:
                    x.decompose()
                    break
            body = to_markdown(str(tds[1]), link)
            body = re.sub(r"^\s*11\s*<sub>ο\s*</sub>\s*", "", body)
            write(f"collections/_events/{d}-{slugify(t, 50)}.md", {
                "title": t, "date": d, "dates_text": when, "type": "conference", "website": href,
                "legacy_url": "/seminaria_synedria"}, body)
            ev += 1
    return n, ev


def sector_for_seminar(t):
    t = t.lower()
    if "στατιστ" in t:
        return "statistiki"
    if "ανάλυσ" in t and "εφαρμοσ" not in t:
        return "analysi"
    if "εφαρμοσμ" in t:
        return "efarmosmena"
    if "γεωμετρ" in t or "αλγεβρ" in t and "τελεστ" not in t:
        return "algebra-geometria"
    return None


GR_MONTHS = {"ιανουαρ": 1, "φεβρουαρ": 2, "μαρτ": 3, "απριλ": 4, "μαΐ": 5, "μαι": 5, "ιουν": 6, "ιουλ": 7,
             "αυγουστ": 8, "σεπτεμβρ": 9, "οκτωβρ": 10, "νοεμβρ": 11, "δεκεμβρ": 12}


def parse_greek_date(text):
    import unicodedata
    t = unicodedata.normalize("NFD", text.lower())
    t = unicodedata.normalize("NFC", "".join(c for c in t if unicodedata.category(c) != "Mn"))
    m = re.search(r"(\d{1,2})(?:\s*[-–]\s*\d{1,2})?\s+([α-ωάέήίόύώϊΐ]+)\s+(\d{4})", t)
    if not m:
        m2 = re.search(r"(\d{1,2})[./](\d{1,2})[./](\d{4})", t)
        if m2:
            return date(int(m2.group(3)), int(m2.group(2)), int(m2.group(1))).isoformat()
        return None
    mon = next((v for k, v in GR_MONTHS.items() if m.group(2).startswith(k)), None)
    if not mon:
        return None
    try:
        return date(int(m.group(3)), mon, int(m.group(1))).isoformat()
    except ValueError:
        return None


# ------------------------------------------------------------------ static pages & programs
def import_pages():
    for old, (permalink, section, nav, title, nav_title) in PAGES.items():
        if old not in RECS:
            REPORT.append(f"page missing from crawl: {old}")
            continue
        fname = "pages" + permalink.rstrip("/") + ".md"
        fm = {"title": title or title_of(old), "nav_title": nav_title, "permalink": permalink,
              "section": section, "nav_order": nav, "legacy_url": old}
        if old == "/to_tmima":
            fm.update({"section_root": True, "nav_order": 1, "nav_title": "Το Τμήμα"})
            fname = "pages/to-tmima/index.md"
        write(fname, fm, md_of(old))
    for old, (key, title, nav, parent, sector) in PROGRAMS.items():
        if old not in RECS:
            continue
        fm = {"title": title, "key": key, "section": "spoudes", "nav_order": nav, "parent_program": parent,
              "legacy_url": old}
        if parent:
            fm["parent_url"] = f"/spoudes/{parent}/"
        write(f"collections/_programs/{key}.md", fm, md_of(old))
    # computer lab
    p = "/to_tmima/ergastiria_i/y"
    write("collections/_labs/ergastirio-ypologiston.md",
          {"title": "Εργαστήριο Υπολογιστών", "kind": "teaching", "legacy_url": p}, md_of(p))
    # masters theses pages are long lists; keep them as pages for now
    for old in RECS:
        if "diplomatikes_ergasies" in old:
            slug = {"efarmosmenon": "efarmosmena", "statistikis": "statistiki", "theoritikon": "theoritika"}
            k = next(v for kk, v in slug.items() if kk in old)
            write(f"pages/spoudes/diplomatikes-{k}.md", {
                "title": title_of(old), "permalink": f"/spoudes/metaptychiakes/diplomatikes/{k}/",
                "section": "spoudes", "parent_url": "/spoudes/metaptychiakes/", "parent_title": "Μεταπτυχιακές σπουδές",
                "legacy_url": old}, md_of(old))
            FIXED[old] = f"/spoudes/metaptychiakes/diplomatikes/{k}/"
    # remaining intro texts used by hand-written landing pages
    for old, dest in [("/diakriseis_melon_tmimatos", "_migration/intro/diakriseis.md"),
                      ("/chrisimoi_syndesmoi", "_migration/intro/syndesmoi.md"),
                      ("/to_tmima/istorika_stoicheia/diatelesantes_proedroi_kai_an_proedroi_toy_tmimatos", "_migration/intro/proedroi.md"),
                      ("/anthropino_dynamiko", "_migration/intro/anthropino.md"),
                      ("/chrisima_entypa", "_migration/intro/entypa.md")]:
        os.makedirs(os.path.join(ROOT, "_migration/intro"), exist_ok=True)
        with open(os.path.join(ROOT, dest), "w") as f:
            f.write(md_of(old))


def import_chairs():
    md = open(os.path.join(ROOT, "_migration/intro/proedroi.md")).read()
    notes = dict(re.findall(r"<sup>(\d+)</sup>\s*(.+)", md))
    n = 0
    for row in re.findall(r"^\| (\d[^|]*?) \| (.+?) \|$", md, flags=re.M):
        term, cell = row
        dates = re.findall(r"\d{1,2}\.\d{1,2}\.\d{4}", term)
        to_iso = lambda d: "%s-%02d-%02d" % (d.split(".")[2], int(d.split(".")[1]), int(d.split(".")[0]))
        start = to_iso(dates[0])
        end = to_iso(dates[1]) if len(dates) > 1 else None
        foot = [notes[k] for k in re.findall(r"<sup>(\d+)</sup>", cell) if k in notes]
        cell = re.sub(r"<sup>\d+</sup>", "", cell)
        chair = re.search(r"\*\*Πρόεδρος:\*\*\s*([^<*]+)", cell)
        vices = []
        for m in re.finditer(r"\*\*Αν\. Πρόεδρος:\*\*\s*([^<*]+)(?:<br>\s*\(([^)]+)\))?", cell):
            v = {"name": m.group(1).strip()}
            if m.group(2):
                v["period"] = m.group(2).strip()
            vices.append(v)
        write(f"collections/_chairs/{start}.md", {"term_start": start, "term_end": end,
              "chair": chair.group(1).strip() if chair else None, "vice_chairs": vices, "notes": foot,
              "legacy_url": "/to_tmima/istorika_stoicheia/diatelesantes_proedroi_kai_an_proedroi_toy_tmimatos"})
        n += 1
    return n


def clean_generated():
    """Remove files written by a previous run (`generated: true`) that have Greek content.
    Their en: blocks are remembered and written back. Hand-edited files are kept."""
    n = 0
    files = glob.glob(os.path.join(ROOT, "collections/_*/*.md")) + glob.glob(os.path.join(ROOT, "pages/**/*.md"), recursive=True)
    for f in files:
        fm, _ = by.read(f)
        if fm.get("generated") and fm.get("el"):
            if fm.get("en"):
                KEPT_EN[os.path.relpath(f, ROOT)] = fm["en"]
            os.remove(f)
            n += 1
    return n


if __name__ == "__main__":
    if OVERWRITE:
        print("removed stale generated files:", clean_generated())
    n_news = import_news()
    import_pages()
    ppl = import_people()
    n_th = import_theses()
    n_forms = import_forms()
    n_aw = import_awards()
    n_sem, n_ev = import_seminars()
    print("chairs", import_chairs())
    import_pages()  # second pass: links to diplomatikes now resolve
    print(f"news {n_news}, people {len(ppl)}, theses {n_th}, forms {n_forms}, awards {n_aw}, seminars {n_sem}, conferences {n_ev}")
    with open(os.path.join(ROOT, "_migration/import-report.txt"), "w") as f:
        f.write("\n".join(sorted(set(REPORT))) + "\n")
    print(len(set(REPORT)), "report lines")
