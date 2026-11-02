"""Parse staff listings of the old site into person records."""
import re

from bs4 import BeautifulSoup

AT = r"\s*[\[\(]\s*(?:AT|at|ΑΤ|ατ|Αt)\s*[\]\)]\s*"
EMAIL = re.compile(r"([A-Za-z0-9._%+-]+)(?:" + AT + r"|@)([A-Za-z0-9.-]+\.[a-z]{2,})")
PHONE = re.compile(r"(?:Τηλ[^:]*:)\s*([\d\-\s/()+]{7,})")
OFFICE = re.compile(r"Γραφείο\s*:?\s*:?\s*([^,\n]+?)\s*(?:,|Τηλ|e-?mail|$)", re.I)

SECTORS = {
    "άλγεβρας": "algebra-geometria",
    "ανάλυσης": "analysi",
    "στατιστικής": "statistiki",
    "διδακτικής": "didaktiki",
    "εφαρμοσμένων": "efarmosmena",
}
RANKS = [
    ("Ομότιμ", "Ομότιμος Καθηγητής"),
    ("Αναπληρωτ", "Αναπληρωτής Καθηγητής"),
    ("Επίκουρ", "Επίκουρος Καθηγητής"),
    ("Καθηγ", "Καθηγητής"),
]
FEMALE_RANK = {
    "Καθηγητής": "Καθηγήτρια",
    "Αναπληρωτής Καθηγητής": "Αναπληρώτρια Καθηγήτρια",
    "Επίκουρος Καθηγητής": "Επίκουρη Καθηγήτρια",
    "Ομότιμος Καθηγητής": "Ομότιμη Καθηγήτρια",
}


def sector_key(text):
    t = text.lower()
    for k, v in SECTORS.items():
        if k in t:
            return v
    return None


def norm_rank(text):
    """Canonical (masculine) rank used for grouping; display form kept separately."""
    for stem, rank in RANKS:
        if stem.lower() in text.lower():
            return rank
    return None


def blocks(html):
    s = BeautifulSoup(html, "html.parser")
    root = s.select_one(".single_page--content") or s
    for br in root.find_all("br"):
        br.replace_with("\n")
    for p in root.find_all(["p", "h2", "h3", "li"]):
        p.insert_after("\n")
    # keep first link (personal homepage) per block
    for a in root.find_all("a"):
        href = a.get("href", "")
        if href.startswith("http") and "math.uoa.gr" not in href:
            a.replace_with(f"{a.get_text()}⟦{href}⟧")
    text = root.get_text()
    text = text.replace("\xa0", " ")
    heading = None
    out = []
    # Track h2 headings (rank groups on sector pages) by marking them
    for chunk in re.split(r"►", text)[1:]:
        out.append(chunk)
    return out


def parse_block(chunk):
    raw = re.sub(r"[ \t]+", " ", chunk).strip()
    lines = [l.strip(" ,*") for l in raw.split("\n") if l.strip(" ,*")]
    if not lines:
        return None
    website = None
    m = re.search(r"⟦(.*?)⟧", raw)
    if m:
        website = m.group(1).strip()
    first = re.sub(r"⟦.*?⟧", "", lines[0])
    name = re.split(r",|Γραφείο|Τομέας|Διδάσκων|Ε\.Τ\.Ε\.Π", first)[0].strip(" ,.*")
    name = re.sub(r"\s+", " ", name)
    # split glued "ΧατζηκαλέαςΑθανάσιος"
    name = re.sub(r"([α-ωάέήίόύώϊϋΐΰ])([Α-ΩΆΈΉΊΌΎΏ])", r"\1 \2", name)
    flat = re.sub(r"⟦.*?⟧", "", " ".join(lines))
    rec = {"title": name}
    if website:
        rec["website"] = website
    em = EMAIL.search(flat)
    if em:
        rec["email"] = f"{em.group(1)}@{em.group(2)}".rstrip(".")
    ph = PHONE.search(flat)
    if ph:
        p = re.sub(r"\s+", "", ph.group(1)).strip("-,")
        if len(re.sub(r"\D", "", p)) >= 7:
            rec["phone"] = p if not re.fullmatch(r"727-?\d{4}", p) else "210-" + p
    of = OFFICE.search(flat)
    if of:
        o = of.group(1).strip(" :.-")
        if o and o not in ("--",) and len(o) < 40:
            rec["office"] = o
    it = re.search(r"Ερευνητικά Ενδιαφέροντα\s*:?\s*(.*?)(?:Γνωστικό|Γραφείο|$)", flat)
    if it:
        v = it.group(1).strip(" :.")
        if v:
            rec["interests"] = v.lstrip(". ")
    ga = re.search(r"Γνωστικό Αντικείμενο\s*:?\s*(.*?)(?:Ερευνητικά|Γραφείο|$)", flat)
    if ga and ga.group(1).strip(" :."):
        rec["field"] = ga.group(1).strip(" :.")
    # rank + sector usually on the second line: "Καθηγητής, Τομέας Άλγεβρας Γεωμετρίας."
    head = " ".join(lines[:3])
    r = norm_rank(head.split("Ερευνητικά")[0]) if re.search(r"Καθηγ", head) else None
    if r:
        rec["rank"] = r
        mm = re.search(r"(Ομότιμ\w*|Αναπληρ\w*|Επίκουρ\w*)?\s*(Καθηγ\w+)", head)
        if mm:
            rec["rank_display"] = mm.group(0).strip()
    sk = None
    ts = re.search(r"Τομέας\s*:?\s*([^\n,.]+)", flat)
    if ts:
        sk = sector_key(ts.group(1))
    if sk:
        rec["sector"] = sk
    rec["_raw"] = flat
    return rec


def parse_people(html):
    return [r for r in (parse_block(b) for b in blocks(html)) if r and len(r["title"]) > 3]
