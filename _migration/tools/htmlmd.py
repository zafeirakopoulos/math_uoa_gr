"""Minimal TYPO3-HTML → Markdown converter + Greek slug helper (ELOT 743-ish)."""
import re
import unicodedata

from bs4 import BeautifulSoup, Comment, NavigableString, Tag

# ---------------------------------------------------------------- slugs
_GR = {
    "α": "a", "β": "v", "γ": "g", "δ": "d", "ε": "e", "ζ": "z", "η": "i", "θ": "th",
    "ι": "i", "κ": "k", "λ": "l", "μ": "m", "ν": "n", "ξ": "x", "ο": "o", "π": "p",
    "ρ": "r", "σ": "s", "ς": "s", "τ": "t", "υ": "y", "φ": "f", "χ": "ch", "ψ": "ps", "ω": "o",
}
_DIGRAPHS = [("ου", "ou"), ("αυ", "av"), ("ευ", "ev"), ("ηυ", "iv"),("μπ", "b"), ("ντ", "nt"), ("γκ", "gk"), ("αι", "ai"), ("ει", "ei"), ("οι", "oi")]


def slugify(text, maxlen=70):
    s = unicodedata.normalize("NFD", text.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = unicodedata.normalize("NFC", s)
    for a, b in _DIGRAPHS:
        s = s.replace(a, b)
    s = "".join(_GR.get(c, c) for c in s)
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    if len(s) > maxlen:
        s = s[:maxlen].rsplit("-", 1)[0]
    return s


# ---------------------------------------------------------------- html → md
INLINE_STRIP = {"span", "font", "u", "small", "big", "abbr", "sup", "sub", "label"}


def clean_soup(html):
    s = BeautifulSoup(html, "html.parser")
    for c in s.find_all(string=lambda t: isinstance(t, Comment)):
        c.extract()
    for t in s.find_all(["script", "style", "meta", "form", "noscript", "iframe"]):
        t.decompose()
    for t in s.select(".frame-type-menu_pages, .news-backlink-wrap, .social_share"):
        t.decompose()
    for t in s.find_all(INLINE_STRIP):
        if t.name in ("sup", "sub"):
            continue
        t.unwrap()
    for t in s.find_all("div"):
        t.unwrap()
    return s


def _text(node):
    return re.sub(r"\s+", " ", str(node))


class MD:
    def __init__(self, link_fn=None):
        self.link_fn = link_fn or (lambda h: h)

    def inline(self, node):
        out = []
        for ch in node.children:
            if isinstance(ch, NavigableString):
                t = _text(ch)
                t = re.sub(r"([*_`\[\]])", r"\\\1", t)
                out.append(t)
            elif isinstance(ch, Tag):
                n = ch.name
                inner = self.inline(ch)
                if n in ("strong", "b"):
                    out.append(self._wrap(inner, "**"))
                elif n in ("em", "i"):
                    out.append(self._wrap(inner, "*"))
                elif n == "br":
                    out.append("  \n")
                elif n == "a":
                    href = ch.get("href", "")
                    if not href or href.startswith("#"):
                        out.append(inner)
                    else:
                        href = self.link_fn(href)
                        label = inner.strip() or href
                        out.append(f"[{label}]({href})")
                elif n == "img":
                    src = ch.get("src", "")
                    if src:
                        out.append(f"![{ch.get('alt', '').strip()}]({self.link_fn(src)})")
                elif n in ("sup", "sub"):
                    out.append(f"<{n}>{inner}</{n}>")
                elif n == "code":
                    out.append(f"`{ch.get_text()}`")
                else:
                    out.append(inner)
        return "".join(out)

    @staticmethod
    def _wrap(inner, mark):
        st = inner.strip()
        if not st:
            return inner
        lead = inner[: len(inner) - len(inner.lstrip())]
        trail = inner[len(inner.rstrip()):]
        return f"{lead}{mark}{st}{mark}{trail}"

    def block(self, node, depth=0):
        parts = []
        buf = []

        def flush():
            t = "".join(buf).strip()
            if t:
                parts.append(t)
            buf.clear()

        for ch in node.children:
            if isinstance(ch, NavigableString):
                buf.append(re.sub(r"\s+", " ", str(ch)))
                continue
            if not isinstance(ch, Tag):
                continue
            n = ch.name
            if n in ("p", "address"):
                flush()
                t = self.inline(ch).strip()
                t = re.sub(r"^(\s*\*\*\s*\*\*)+", "", t).strip()
                if t and t not in ("&nbsp;", "\xa0"):
                    parts.append(t)
            elif re.fullmatch(r"h[1-6]", n):
                flush()
                lvl = max(2, min(4, int(n[1])))
                t = re.sub(r"\*\*(.*?)\*\*", r"\1", self.inline(ch).strip())
                if t:
                    parts.append("#" * lvl + " " + t)
            elif n in ("ul", "ol"):
                flush()
                parts.append(self.list_(ch, n == "ol", depth))
            elif n == "table":
                flush()
                parts.append(self.table(ch))
            elif n == "blockquote":
                flush()
                inner = self.block(ch, depth)
                parts.append("\n".join("> " + l if l else ">" for l in inner.split("\n")))
            elif n == "hr":
                flush()
                parts.append("---")
            elif n in ("figure", "section", "article", "header", "footer", "main", "center"):
                flush()
                parts.append(self.block(ch, depth))
            else:
                buf.append(self.block(ch, depth) if n in ("dl",) else self.inline(ch) if n != "br" else "  \n")
        flush()
        return "\n\n".join(p for p in parts if p.strip())

    def list_(self, node, ordered, depth):
        lines = []
        for i, li in enumerate(node.find_all("li", recursive=False), 1):
            nested = [c for c in li.find_all(["ul", "ol"], recursive=False)]
            for c in nested:
                c.extract()
            bullet = f"{i}." if ordered else "-"
            text = self.block(li, depth + 1).replace("\n\n", "\n").strip()
            text = text.replace("\n", "\n" + "  " * (depth + 1))
            lines.append("  " * depth + f"{bullet} {text}")
            for c in nested:
                lines.append(self.list_(c, c.name == "ol", depth + 1))
        return "\n".join(l for l in lines if l.strip())

    def table(self, node):
        rows = node.find_all("tr")
        if not rows:
            return ""
        cells = [[self.inline(c).replace("|", "\\|").replace("  \n", "<br>").strip() for c in r.find_all(["td", "th"])] for r in rows]
        width = max(len(r) for r in cells)
        if width == 1:
            return "\n\n".join(r[0] for r in cells if r and r[0])
        cells = [r + [""] * (width - len(r)) for r in cells]
        head = cells[0] if rows[0].find("th") else [""] * width
        body = cells[1:] if rows[0].find("th") else cells
        out = ["| " + " | ".join(head) + " |", "|" + "---|" * width]
        out += ["| " + " | ".join(r) + " |" for r in body]
        return "\n".join(out)


def to_markdown(html, link_fn=None):
    s = clean_soup(html)
    root = s.select_one(".single_page--content") or s
    md = MD(link_fn).block(root)
    md = md.replace("\xa0", " ")
    md = re.sub(r"[ \t]+\n", lambda m: "  \n" if m.group(0).startswith("  ") else "\n", md)
    md = re.sub(r"\*\*\s*\*\*", "", md)
    md = re.sub(r"\n{3,}", "\n\n", md)
    md = re.sub(r"\[\s*AT\s*\]", "@", md)
    # Word "Symbol" bullets (private-use U+F0B7 etc.) → Markdown list items
    md = re.sub(r"(^|  \n)\s*[\ue000-\uf8ff•·]\s*", lambda m: ("\n" if m.group(1) else "") + "- ", md, flags=re.M)
    # soft-wrapped lines from pasted Word text: a hard break followed by a lowercase letter
    md = re.sub(r"  \n(?=[a-zα-ωάέήίόύώϊϋΐΰ(])", " ", md)
    return md.strip() + "\n"
