"""Shared helpers: read/write Jekyll files in the one-file bilingual format."""
import os
import re

import yaml


class _Dumper(yaml.SafeDumper):
    pass


def _str(dumper, s):
    if "\n" in s:
        # literal blocks cannot carry trailing spaces → Markdown hard breaks become <br>
        s = re.sub(r"[ \t]+\n", lambda m: "<br>\n" if len(m.group(0)) >= 3 else "\n", s)
        s = s.rstrip() + "\n"
        return dumper.represent_scalar("tag:yaml.org,2002:str", s, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", s)


_Dumper.add_representer(str, _str)


def dump(fm):
    return yaml.dump(fm, Dumper=_Dumper, allow_unicode=True, sort_keys=False, width=1000).strip()


def read(path):
    s = open(path).read()
    m = re.match(r"---\n(.*?)\n---\n?(.*)", s, re.S)
    if not m:
        return {}, s
    return (yaml.safe_load(m.group(1)) or {}), m.group(2)


def write(path, fm, body=""):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        f.write(f"---\n{dump(fm)}\n---\n")
        if body and body.strip():
            f.write("\n" + body.strip() + "\n")


def clean(d):
    """Drop empty values recursively."""
    if isinstance(d, dict):
        return {k: clean(v) for k, v in d.items() if v not in (None, "", [], {})}
    return d


# fields that differ per language (everything else is shared)
LANG_FIELDS = {
    "title", "nav_title", "lede", "summary", "singular", "rank_display", "interests", "duties", "field",
    "rank_titles", "author", "supervisor", "legacy_url", "description", "dates_text", "chair", "vice_chairs",
    "notes", "actions", "tiles", "speaker_note", "body", "parent_url", "parent_title",
}
