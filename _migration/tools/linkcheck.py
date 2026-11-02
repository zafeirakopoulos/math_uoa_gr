"""Check internal links/assets in the built _site. usage: linkcheck.py SITE_DIR"""
import os, re, sys
from collections import defaultdict
from urllib.parse import unquote, urlparse
site = sys.argv[1]
bad = defaultdict(set)
for dp, _, fs in os.walk(site):
    for f in fs:
        if not f.endswith(".html"):
            continue
        src = os.path.join(dp, f)
        html = open(src, errors="ignore").read()
        for u in re.findall(r'(?:href|src)="([^"#?]+)', html):
            if u.startswith(("http", "mailto:", "tel:", "data:", "//")):
                continue
            path = unquote(urlparse(u).path)
            target = os.path.join(site, path.lstrip("/"))
            if path.endswith("/"):
                target = os.path.join(target, "index.html")
            if not os.path.exists(target) and not os.path.exists(target + ".html"):
                bad[path].add(os.path.relpath(src, site))
for k, v in sorted(bad.items()):
    print(k, "<-", ", ".join(sorted(v)[:3]), f"(+{len(v)-3})" if len(v) > 3 else "")
print(len(bad), "broken internal targets")
