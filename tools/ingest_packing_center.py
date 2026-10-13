"""Build registry entries from four tables of Erich Friedman's Packing Center.

  curl -L -o cirinsqu.html https://erich-friedman.github.io/packing/cirinsqu/
  curl -L -o cirincir.html https://erich-friedman.github.io/packing/cirincir/
  curl -L -o triinsqu.html https://erich-friedman.github.io/packing/triinsqu/
  curl -L -o squinsqu.html https://kingbird.myphotos.cc/packing/squares_in_squares.html
  python tools/ingest_packing_center.py cirinsqu.html cirincir.html triinsqu.html squinsqu.html \
      [--append data/entries.jsonl]

Stdlib only; the pages are parsed as text and never rendered. The Packing Center links its
squares-in-squares table to David Ellsworth's updated copy (kingbird.myphotos.cc), which is the
one read here. One entry per n <= 50 that a page gives a value for. A cell the page marks
"Proved" or "Trivial." is `exact`; every other cell is a `record` (smallest known container).
Decimals are printed truncated on the pages ("3.931+", "\\Nn{2.70710678118654}"); they are kept
as strings ending in "+", meaning the true value is slightly larger. Integer sides stay numbers.
The squares page states that every unpictured n <= 324 has the trivial packing (side
ceil(sqrt n)) as its best known packing; those cells are `record` entries with that side.
"""

import argparse
import hashlib
import html
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import dump_jsonl, load_jsonl

NMAX = 50
SCHEME = "PackingCenter"
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]

TABLES = {
    "cirinsqu": dict(
        url="https://erich-friedman.github.io/packing/cirinsqu/",
        revision="2026-10-09",
        title="Circles in Squares",
        variant="Packing %d unit circles in the smallest square",
        text="s(%d) = the smallest side of a square that contains %d non-overlapping circles of radius 1.",
        latex=r"s(%d)=\min\{s:\ %d\text{ disjoint open unit disks fit in }[0,s]^2\}",
        domain="arrangements of unit disks in a square",
        units="side length of the square; circles have radius 1",
    ),
    "cirincir": dict(
        url="https://erich-friedman.github.io/packing/cirincir/",
        revision="2026-10-09",
        title="Circles in Circles",
        variant="Packing %d unit circles in the smallest circle",
        text="r(%d) = the smallest radius of a circle that contains %d non-overlapping circles of radius 1.",
        latex=r"r(%d)=\min\{r:\ %d\text{ disjoint open unit disks fit in a disk of radius }r\}",
        domain="arrangements of unit disks in a disk",
        units="radius of the container circle; circles have radius 1",
    ),
    "triinsqu": dict(
        url="https://erich-friedman.github.io/packing/triinsqu/",
        revision="2026-10-09",
        title="Triangles in Squares",
        variant="Packing %d unit equilateral triangles in the smallest square",
        text="s(%d) = the smallest side of a square that contains %d non-overlapping equilateral triangles of side 1.",
        latex=r"s(%d)=\min\{s:\ %d\text{ interior-disjoint unit equilateral triangles fit in }[0,s]^2\}",
        domain="arrangements of unit equilateral triangles in a square",
        units="side length of the square; triangles have side 1",
    ),
    "squinsqu": dict(
        url="https://kingbird.myphotos.cc/packing/squares_in_squares.html",
        revision="2026-09-24",
        title="Squares in Squares (updated by David Ellsworth from the Packing Center table)",
        variant="Packing %d unit squares in the smallest square",
        text="s(%d) = the smallest side of a square that contains %d non-overlapping squares of side 1.",
        latex=r"s(%d)=\min\{s:\ %d\text{ interior-disjoint unit squares fit in }[0,s]^2\}",
        domain="arrangements of unit squares (rotations allowed) in a square",
        units="side length of the square; squares have side 1",
    ),
}


def _plain(fragment):
    t = re.sub(r"<br\s*/?>", " | ", fragment, flags=re.IGNORECASE)
    t = html.unescape(re.sub(r"<[^>]+>", "", t))
    return re.sub(r"\s+", " ", t).strip(" |")


def _value(s_text):
    """'s = 2 + 12/sqrt13 = 5.328+' -> ('5.328+', closed form); 's = 6' -> (6, None)."""
    m = re.search(r"\\Nn\{([0-9.]+)\}", s_text)
    if m:
        return m.group(1) + "+", s_text
    m = re.search(r"=\s*([0-9]*\.[0-9]+)\+", s_text)
    if m:
        v = m.group(1)
        return ("0" + v if v.startswith(".") else v) + "+", s_text
    m = re.search(r"=\s*([0-9]+)\s*\$?\s*$", s_text.strip())
    if m:
        return int(m.group(1)), None
    raise ValueError("no value in %r" % s_text)


def parse_friedman(page):
    """Old-style Packing Center page: an "n." label in a size+3 font, then "s = ..." and the
    attribution in a size+1 font, in document order (both the grid and the later stacked layout)."""
    page = re.sub(r"<!--.*?-->", "", page, flags=re.DOTALL)
    parts = re.split(r"<font size=\+([13])>", page, flags=re.IGNORECASE)
    labels, values = [], []
    for size, body in zip(parts[1::2], parts[2::2]):
        body = re.split(r"<t[dr]|</t[dr]|<p>|<hr|<font", body, flags=re.IGNORECASE)[0]
        p = _plain(body)
        m = re.match(r"^(\d+)\.", p)
        if size == "3" and m:
            labels.append(int(m.group(1)))
        elif size == "1" and re.match(r"^[sr] = ", p):
            values.append(p)
    if len(labels) != len(values):
        raise ValueError("%d labels vs %d values" % (len(labels), len(values)))
    out = {}
    for n, p in zip(labels, values):
        s_part, _, holder = p.partition(" | ")
        out[n] = (s_part, holder.replace(" | ", " ").strip())
    return out


def parse_ellsworth(page):
    page = re.sub(r"<!--.*?-->", "", page, flags=re.DOTALL)
    out = {}
    for m in re.finditer(
        r'<div class="box"><font size="\+3">(.*?)<br>.*?<div align="center"><font size="\+1">(.*?)</font></div></div>',
        page,
        re.DOTALL,
    ):
        body = re.sub(r'<span class="frames">.*?</span>', "", m.group(2), flags=re.DOTALL)
        p = _plain(body)
        s_part, _, holder = p.partition(" | ")
        for n in (int(x) for x in re.findall(r"\d+", m.group(1))):
            out[n] = (
                s_part.strip("$ "),
                holder.replace("Explore group", "").replace(" | ", " ").strip(" |"),
            )
    return out


def _first_date(holder):
    """Date of the first clause ("Found by X in July 2008", "Proved by Y in 1964")."""
    m = re.search(r"(?:(%s)\s+)?((?:19|20)\d\d)" % "|".join(MONTHS), holder)
    if not m:
        return None
    return m.group(2) + ("-%02d" % (MONTHS.index(m.group(1)) + 1) if m.group(1) else "")


def cells(table, page):
    rows = parse_ellsworth(page) if table == "squinsqu" else parse_friedman(page)
    out = []
    for n in range(1, NMAX + 1):
        if n in rows:
            s_text, holder = rows[n]
            value, closed = _value(s_text)
            exact = holder.startswith("Trivial") or "Proved" in holder
            out.append(
                dict(
                    n=n,
                    value=value,
                    closed=closed,
                    holder=holder,
                    exact=exact,
                    implied=False,
                )
            )
        elif table == "squinsqu":
            out.append(
                dict(
                    n=n,
                    value=math.isqrt(n - 1) + 1,
                    closed=None,
                    holder="",
                    exact=False,
                    implied=True,
                )
            )
    return out


def entry_for(table, c, eid, sha):
    t = TABLES[table]
    n = c["n"]
    holder = c["holder"]
    if len(holder) > 240:
        holder = holder[:237].rsplit(" ", 1)[0] + " ..."
    if c["implied"]:
        printed = (
            "not pictured; the page states the trivial packing (side ceil(sqrt n) = %d) is the best known"
            % c["value"]
        )
    else:
        printed = "printed %r; %s" % (
            c["closed"] or "s = %s" % c["value"],
            holder or "no attribution printed",
        )
    first = _first_date(holder) if holder else None
    return {
        "id": eid,
        "problem_family": "Packing",
        "variant_name": t["variant"] % n,
        "definition": {
            "text": t["text"] % (n, n),
            "latex": t["latex"] % (n, n),
            "status": "curated",
        },
        "domain": t["domain"],
        "direction": "min",
        "units_or_normalisation": t["units"]
        + "; a trailing '+' marks a decimal printed truncated (true value slightly larger)",
        "current_value": c["value"],
        "value_kind": "exact" if c["exact"] else "record",
        "certificate": {
            "file": None,
            "sha256": None,
            "verifier_command": None,
            "verifier_kind": "external",
            "verified_date": None,
            "value_pattern": None,
            "tolerance": None,
        },
        "source": {
            "citation": "E. Friedman, Erich's Packing Center, %s (page last modified %s)"
            % (t["title"], t["revision"]),
            "url": t["url"],
            "date": t["revision"],
            "refereed": False,
        },
        "superseded": [],
        "aliases": [{"scheme": SCHEME, "id": "%s n=%d" % (table, n)}],
        "status": "current",
        "last_checked": "2026-10-12",
        "conflation_note": None,
        "notes": "Parsed from the %s page (sha256 %s) by tools/ingest_packing_center.py; %s.%s"
        % (
            table,
            sha,
            printed,
            " The page marks this cell proved optimal." if c["exact"] else "",
        ),
        "provenance": {
            "setter_kind": "unknown",
            "literature_status": "unknown",
            "first_public_date": first,
            "platform_or_paper": t["url"],
            "basis": "record holder and date as printed on the page: %s"
            % (holder or "none printed"),
        },
        "fidelity": {
            "statement_audit": "self",
            "audit_note": "Standard container-packing definition, transcribed by the maintainers from the page header.",
        },
        "feasibility": None,
    }


def build(pages, start_id):
    """pages: {table: html text}. Returns entries with consecutive ids from start_id."""
    out = []
    for table in TABLES:
        if table not in pages:
            continue
        sha = hashlib.sha256(pages[table].encode("utf-8")).hexdigest()
        for c in cells(table, pages[table]):
            out.append(entry_for(table, c, "EV-%06d" % (start_id + len(out)), sha))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "pages",
        nargs="+",
        help="saved pages, named <table>.html (cirinsqu, cirincir, triinsqu, squinsqu)",
    )
    ap.add_argument(
        "--append", help="entries.jsonl to append to (ids continue from its last id)"
    )
    a = ap.parse_args(argv)
    pages = {}
    for p in a.pages:
        name = os.path.splitext(os.path.basename(p))[0]
        if name not in TABLES:
            ap.error("unknown table %r" % name)
        with open(p, encoding="utf-8") as fh:
            pages[name] = fh.read()
    existing = load_jsonl(a.append) if a.append else []
    start = max([int(e["id"][3:]) for e in existing] or [0]) + 1
    taken = {(x["scheme"], x["id"]) for e in existing for x in e["aliases"]}
    new = [
        e for e in build(pages, start) if (SCHEME, e["aliases"][0]["id"]) not in taken
    ]
    for i, e in enumerate(new):
        e["id"] = "EV-%06d" % (start + i)
    if a.append:
        with open(a.append, "a", encoding="utf-8", newline="\n") as fh:
            fh.write(dump_jsonl(new))
    else:
        sys.stdout.write(dump_jsonl(new))
    print(
        "%d Packing Center entries (%d exact)"
        % (len(new), sum(e["value_kind"] == "exact" for e in new)),
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
