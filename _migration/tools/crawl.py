"""Polite BFS crawl of www.math.uoa.gr static pages + recent announcements.

Writes one JSON record per page into OUT_DIR.
usage: python3 -I crawl.py OUT_DIR [NEWS_LIST_PAGES]
"""
import hashlib
import json
import os
import re
import sys
import time
from urllib.parse import unquote, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

OUT = sys.argv[1]
NEWS_LIST_PAGES = int(sys.argv[2]) if len(sys.argv) > 2 else 6
BASE = os.environ.get("CRAWL_BASE", "https://www.math.uoa.gr")
HOST = BASE.split("//", 1)[1]
NEWS_LIST = os.environ.get("CRAWL_NEWS_LIST", "/anakoinoseis_kai_ekdiloseis/anakoinoseis")
NEWS_MARK = tuple(os.environ.get("CRAWL_NEWS_MARK", "/proboli_anakoinosis/").split(","))
SKIP = ("/fileadmin", "/typo3", "/anazitisi", "/search", "/page",
        "/anakoinoseis_kai_ekdiloseis/proboli_ekdiloseon",
        "/anakoinoseis_kai_ekdiloseis/proboli_ekdilosis")
MAX_PAGES = 600

S = requests.Session()
S.headers["User-Agent"] = "Mozilla/5.0 (math.uoa.gr migration crawler)"


def fetch(path):
    for _ in range(3):
        try:
            r = S.get(BASE + path, timeout=40)
            if r.status_code == 200 and "text/html" in r.headers.get("content-type", ""):
                return r.text
            return None
        except requests.RequestException:
            time.sleep(2)
    return None


def norm(href, cur):
    if not href or href.startswith(("mailto:", "tel:", "#", "javascript:")):
        return None
    u = urlparse(urljoin(BASE + cur, href))
    if u.netloc not in (HOST,) or u.query:
        return None
    p = unquote(u.path).rstrip("/") or "/"
    if p.startswith(SKIP) or "/page/" in p or re.search(r"\.(pdf|docx?|xlsx?|jpe?g|png|gif|zip|pptx?|rar)$", p, re.I):
        return None
    return p


def save(path, html, kind):
    s = BeautifulSoup(html, "html.parser")
    c = s.select_one(".single_page--content") or s.select_one("#page-content")
    crumbs = [a.get_text(" ", strip=True) for a in s.select(".breadcrumbs a")]
    h = s.select_one("#page-content h1") or s.select_one("h1") or s.title
    rec = {
        "path": path,
        "kind": kind,
        "title": h.get_text(" ", strip=True) if h else path,
        "head_title": s.title.get_text(strip=True) if s.title else "",
        "crumbs": crumbs,
        "content": str(c) if c else "",
    }
    t = s.select_one("#page-content time[datetime]")
    if t:
        rec["date"] = t["datetime"]
    fn = hashlib.md5(path.encode()).hexdigest()[:12] + ".json"
    with open(os.path.join(OUT, fn), "w") as f:
        json.dump(rec, f, ensure_ascii=False)
    return s, c


def main():
    seen, queue, news = set(), ["/"], set()
    queued = {"/"}
    while queue:
        p = queue.pop(0)
        if p in seen:
            continue
        seen.add(p)
        html = fetch(p)
        time.sleep(0.3)
        if not html:
            continue
        s, c = save(p, html, "page")
        anchors = s.select("#mainnavigation a, nav a, .sidebar a") + (c.find_all("a") if c else [])
        for a in anchors:
            q = norm(a.get("href"), p)
            if not q:
                continue
            if any(m in q for m in NEWS_MARK):
                news.add(q)
            elif q not in queued and len(queued) < MAX_PAGES:
                queued.add(q)
                queue.append(q)
        print(len(seen), p, file=sys.stderr, flush=True)

    for n in range(1, NEWS_LIST_PAGES + 1):
        html = fetch(f"{NEWS_LIST}/page/{n}")
        time.sleep(0.3)
        if not html:
            break
        for a in BeautifulSoup(html, "html.parser").select(".article__title a"):
            q = norm(a.get("href"), "/")
            if q:
                news.add(q)
    for q in sorted(news):
        html = fetch(q)
        time.sleep(0.3)
        if html:
            save(q, html, "news")
            print("news", q, file=sys.stderr, flush=True)
    print("pages", len(seen), "news", len(news))


if __name__ == "__main__":
    main()
