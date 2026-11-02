"""Crop + shrink a pdftocairo SVG of the official UoA logo sheet.

Keeps only shapes inside the crop box, inlines glyph <use> references as paths,
rounds coordinates and merges everything into one <path> per colour.

usage: python3 -I svgopt.py SRC DST x0 y0 x1 y1 [red=#hex] [ink=#hex]
"""
import re
import sys

src, dst = sys.argv[1], sys.argv[2]
x0, y0, x1, y1 = map(float, sys.argv[3:7])
fills = dict(a.split("=", 1) for a in sys.argv[7:])
MAP = {
    "rgb(70.646667%, 7.588196%, 11.340332%)": fills.get("red", "#B4131D"),
    "rgb(13.729858%, 12.159729%, 12.548828%)": fills.get("ink", "#231F20"),
    # COL2 (Pantone 279 blue emblem) — same role as the red emblem of COL1
    "rgb(35.360718%, 56.010437%, 82.395935%)": fills.get("red", "#5A8FD2"),
}


def num(v):
    return ("%.2f" % v).rstrip("0").rstrip(".")


def shift(d, dx=0.0, dy=0.0):
    toks = re.findall(r"[A-Za-z]|-?\d+\.?\d*", d)
    out, i = [], 0
    while i < len(toks):
        if toks[i].isalpha():
            out.append(toks[i])
            i += 1
        else:
            out += [num(float(toks[i]) + dx), num(float(toks[i + 1]) + dy)]
            i += 2
    return " ".join(out)


def inside(d):
    n = [float(v) for v in re.findall(r"-?\d+\.?\d*", d)]
    xs, ys = n[0::2], n[1::2]
    return xs and max(xs) >= x0 - 1 and min(xs) <= x1 + 1 and max(ys) >= y0 - 1 and min(ys) <= y1 + 1


s = open(src).read()
groups = {}
glyphs = dict(re.findall(r'<g id="(glyph-[\d-]+)">\s*<path[^>]*?d="([^"]*)"', s))
body = re.sub(r"<defs>.*?</defs>", "", s, flags=re.S)

for fill, d in re.findall(r'<path[^>]*?fill="([^"]+)"[^>]*?d="([^"]+)"[^>]*/>', body):
    if fill in MAP and inside(d):
        groups.setdefault(MAP[fill], []).append(shift(d))

for fill, inner in re.findall(r'<g fill="([^"]+)"[^>]*>(.*?)</g>', body, re.S):
    if fill not in MAP:
        continue
    for gid, x, y in re.findall(r'<use xlink:href="#([^"]+)" x="([^"]+)" y="([^"]+)"/>', inner):
        x, y = float(x), float(y)
        if gid in glyphs and x0 - 5 <= x <= x1 + 5 and y0 - 5 <= y <= y1 + 15:
            groups.setdefault(MAP[fill], []).append(shift(glyphs[gid], x, y))

pad = 1.5
vb = "%.1f %.1f %.1f %.1f" % (x0 - pad, y0 - pad, x1 - x0 + 2 * pad, y1 - y0 + 2 * pad)
svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}">'
svg += "".join(f'<path fill="{f}" d="{" ".join(ds)}"/>' for f, ds in groups.items())
svg += "</svg>\n"
open(dst, "w").write(svg)
print(dst, len(svg), {k: len(v) for k, v in groups.items()})
