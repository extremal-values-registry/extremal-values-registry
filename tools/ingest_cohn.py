"""Build registry entries from Henry Cohn's tables of kissing numbers and sphere packing densities.

  curl -L -o kissing-numbers.html https://cohn.mit.edu/kissing-numbers
  curl -L -o sphere-packing.html https://cohn.mit.edu/sphere-packing
  python tools/ingest_cohn.py kissing-numbers.html sphere-packing.html [--append data/entries.jsonl]

Stdlib only; the pages are parsed as text and never rendered. One cell per dimension 1..48. A row
whose lower and upper bound share one cell (colspan 2) is proved and becomes `exact`; every other
row becomes a `bound` entry "L <= tau_n <= U" (kissing) or "L <= Delta_n <= U" (packing density),
with the densities as printed (16 decimals, truncated; the upper bounds are rounded up).

A cell that the registry already holds is not duplicated. With --append, the cells in LINKS get
a `Cohn` alias and a conflation_note on the existing entry instead; LINKED_NEW cells get a new
entry whose conflation_note points to a related but different entry (and that entry gets a note
pointing back).
"""

import argparse
import hashlib
import html
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import dump_jsonl, load_jsonl

SCHEME = "Cohn"
DMAX = 48
PAGES = {
    "kissing-numbers": dict(
        url="https://cohn.mit.edu/kissing-numbers",
        revision="2026-10-11",
        title="Kissing numbers (table of upper and lower bounds)",
    ),
    "sphere-packing": dict(
        url="https://cohn.mit.edu/sphere-packing",
        revision="2026-07-30",
        title="Sphere packing (table of best known densities and upper bounds)",
    ),
}

# Same quantity already in the registry: (page, n) -> [(entry id, alias side or None)].
LINKS = {
    ("kissing-numbers", 5): [("EV-000007", "lower"), ("EV-000228", "upper")],
    ("kissing-numbers", 6): [("EV-000108", "lower")],
    ("kissing-numbers", 9): [("EV-000109", None)],
    ("kissing-numbers", 11): [("EV-000006", "lower")],
    # sup over periodic packings equals the optimal density, so the periodic d=10 entry is this cell
    ("sphere-packing", 10): [("EV-000124", "lower")],
}
# Related but different quantity: (page, n) -> entry id. A new entry is made and both are noted.
LINKED_NEW = {
    (
        "sphere-packing",
        12,
    ): "EV-000101",  # lattice packings only; K12 attains both best known values
}


def _cell(fragment):
    t = re.sub(r"<sup>(.*?)</sup>", r"^\1", fragment, flags=re.DOTALL)
    t = html.unescape(re.sub(r"<[^>]+>", "", t))
    return re.sub(r"\s+", " ", t).strip()


def _num(text):
    return text.replace("…", "").replace(" ", "").strip()


def _short_ref(num, title):
    """'[13] J. Leech and N. J. A. Sloane (1971)': the page's reference number, authors and year."""
    parts = title.split(", ")
    authors = [parts[0]]
    for p in parts[1:]:
        if not re.match(r"^(and )?([A-Z][a-z]?\.\s?)+", p):
            break
        authors.append(p)
    years = re.findall(r"\b(1[89]\d\d|20\d\d)\b", title)
    return "[%s] %s (%s)" % (num, ", ".join(authors), years[-1] if years else "n.d.")


def parse(page):
    """Rows of the first data table: [(n, cells, proved, ref titles)]."""
    i = page.index('id="data"')
    body = page[i : page.index("</table>", i)]
    rows = []
    for r in re.split(r"<tr[^>]*>", body)[1:]:  # the header row has no </tr>
        tds = re.findall(r"<td([^>]*)>(.*?)</td>", r, re.DOTALL)
        if not tds:
            continue
        proved = any("colspan" in attrs for attrs, _ in tds)
        refs = [_short_ref(num, html.unescape(t)) for t, num in re.findall(r'title="([^"]*)" href="#(\d+)"', r)]
        rows.append((int(_cell(tds[0][1])), [_cell(x) for _, x in tds], proved, refs))
    return rows


def cells(page_name, page):
    out = []
    for n, c, proved, refs in parse(page):
        if n > DMAX:
            continue
        if page_name == "kissing-numbers":
            lower = int(_num(c[1]))
            upper = lower if proved else int(_num(c[2]))
            centre = None
        else:  # n, centre density, #, density, upper bound, ratio, refs
            centre = c[1] + (" (%s spheres per lattice cell)" % c[2] if c[2] else "")
            lower = _num(c[3])  # kept as printed; floats would drop trailing zeros
            upper = lower if proved else _num(c[4])
        out.append(
            dict(n=n, lower=lower, upper=upper, proved=proved, refs=refs, centre=centre)
        )
    return out


def entry_for(page_name, c, eid, sha):
    p = PAGES[page_name]
    n = c["n"]
    refs = "; ".join(c["refs"]) or "none listed"
    if page_name == "kissing-numbers":
        sym, fam = "tau_%d" % n, "Sphere packing and kissing"
        variant = "Kissing number in dimension %d" % n
        text = (
            "tau_%d = the maximum number of non-overlapping unit spheres in R^%d that touch a central unit sphere."
            % (n, n)
        )
        latex = (
            r"\tau_{%d}=\max\{|X|:\ X\subset S^{%d},\ \langle x,y\rangle\le\tfrac12\ (x\ne y)\}"
            % (n, n - 1)
        )
        domain, units = "point sets on the unit sphere S^%d" % (n - 1), "count"
    else:
        sym, fam = "Delta_%d" % n, "Sphere packing and kissing"
        variant = "Sphere packing density in dimension %d" % n
        text = (
            "Delta_%d = the supremum of the upper density of packings of congruent balls in R^%d."
            % (n, n)
        )
        latex = (
            r"\Delta_{%d}=\sup_{P}\ \limsup_{r\to\infty}\frac{\mathrm{vol}(P\cap B_r)}{\mathrm{vol}(B_r)}"
            % n
        )
        domain = "packings of congruent balls in R^%d" % n
        units = "fraction of space covered; lower bounds printed truncated to 16 decimals, upper bounds rounded up"
    if c["proved"]:
        value, kind = (c["lower"] if not isinstance(c["lower"], str) else float(c["lower"]) if "." in c["lower"] else int(c["lower"])), "exact"
    else:
        value, kind = "%s <= %s <= %s" % (c["lower"], sym, c["upper"]), "bound"
    centre = "; centre density %s" % c["centre"] if c["centre"] else ""
    return {
        "id": eid,
        "problem_family": fam,
        "variant_name": variant,
        "definition": {"text": text, "latex": latex, "status": "curated"},
        "domain": domain,
        "direction": "unstated",
        "units_or_normalisation": units,
        "current_value": value,
        "value_kind": kind,
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
            "citation": "H. Cohn, %s, page revision %s" % (p["title"], p["revision"]),
            "url": p["url"],
            "date": p["revision"],
            "refereed": False,
        },
        "superseded": [],
        "aliases": [{"scheme": SCHEME, "id": "%s d=%d" % (page_name, n)}],
        "status": "current",
        "last_checked": "2026-10-12",
        "conflation_note": None,
        "notes": "Parsed from %s (sha256 %s) by tools/ingest_cohn.py%s.%s"
        % (
            p["url"],
            sha,
            centre,
            " The table gives one value for both bounds (proved)."
            if c["proved"]
            else "",
        ),
        "provenance": {
            "setter_kind": "unknown",
            "literature_status": "unknown",
            "first_public_date": None,
            "platform_or_paper": "%s ; references listed for the row: %s"
            % (p["url"], refs),
            "basis": "the table cites references per row, not how each bound was found; per-paper provenance is to be filled",
        },
        "fidelity": {
            "statement_audit": "self",
            "audit_note": "Standard definition, transcribed by the maintainers; matches the table's introduction.",
        },
        "feasibility": None,
    }


def _value_text(c, page_name):
    if c["proved"]:
        return "%s (proved)" % c["lower"]
    return "%s to %s" % (c["lower"], c["upper"])


def link_existing(existing, page_name, c):
    """Add a Cohn alias and conflation_note to the entries in LINKS for this cell."""
    by_id = {e["id"]: e for e in existing}
    for eid, side in LINKS[(page_name, c["n"])]:
        e = by_id[eid]
        alias = {"scheme": SCHEME, "id": "%s d=%d" % (page_name, c["n"])}
        if side:
            alias["side"] = side
        if alias not in e["aliases"]:
            e["aliases"].append(alias)
        note = (
            "Same cell as Cohn's table %s, dimension %d (%s, page revision %s); not duplicated."
            % (
                PAGES[page_name]["url"],
                c["n"],
                _value_text(c, page_name),
                PAGES[page_name]["revision"],
            )
        )
        if note not in (e["conflation_note"] or ""):
            e["conflation_note"] = (
                e["conflation_note"] + " " if e["conflation_note"] else ""
            ) + note


def build(pages, start_id, existing=()):
    """pages: {page name: html}. Returns (new entries, ids of existing entries that were linked)."""
    new, touched = [], []
    by_id = {e["id"]: e for e in existing}
    taken = {(x["scheme"], x["id"]) for e in existing for x in e["aliases"]}
    for page_name in PAGES:
        if page_name not in pages:
            continue
        sha = hashlib.sha256(pages[page_name].encode("utf-8")).hexdigest()
        for c in cells(page_name, pages[page_name]):
            key = (page_name, c["n"])
            if (SCHEME, "%s d=%d" % key) in taken and key not in LINKS:
                continue
            if key in LINKS and all(eid in by_id for eid, _ in LINKS[key]):
                link_existing(existing, page_name, c)
                touched += [eid for eid, _ in LINKS[key]]
                continue
            e = entry_for(page_name, c, "EV-%06d" % (start_id + len(new)), sha)
            if key in LINKED_NEW and LINKED_NEW[key] in by_id:
                other = by_id[LINKED_NEW[key]]
                e["conflation_note"] = (
                    "Related to %s (%s), which restricts to lattice packings; the values coincide in this dimension."
                    % (
                        other["id"],
                        other["variant_name"],
                    )
                )
                back = (
                    "Related to %s (Cohn's table, best known density over all packings in dimension %d); same value, different problem."
                    % (e["id"], c["n"])
                )
                if back not in (other["conflation_note"] or ""):
                    other["conflation_note"] = (
                        other["conflation_note"] + " "
                        if other["conflation_note"]
                        else ""
                    ) + back
                touched.append(other["id"])
            new.append(e)
    return new, touched


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "pages",
        nargs="+",
        help="saved pages named kissing-numbers.html / sphere-packing.html",
    )
    ap.add_argument(
        "--append",
        help="entries.jsonl to update (ids continue from its last id; links are written in place)",
    )
    a = ap.parse_args(argv)
    pages = {}
    for p in a.pages:
        name = os.path.splitext(os.path.basename(p))[0]
        if name not in PAGES:
            ap.error("unknown page %r" % name)
        with open(p, encoding="utf-8") as fh:
            pages[name] = fh.read()
    existing = load_jsonl(a.append) if a.append else []
    start = max([int(e["id"][3:]) for e in existing] or [0]) + 1
    taken = {(x["scheme"], x["id"]) for e in existing for x in e["aliases"]}
    new, touched = build(pages, start, existing)
    new = [e for e in new if (SCHEME, e["aliases"][0]["id"]) not in taken]
    for i, e in enumerate(new):
        e["id"] = "EV-%06d" % (start + i)
    if a.append:
        with open(a.append, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(dump_jsonl(existing + new))
    else:
        sys.stdout.write(dump_jsonl(new))
    print(
        "%d Cohn entries (%d exact); linked existing %s"
        % (
            len(new),
            sum(e["value_kind"] == "exact" for e in new),
            ", ".join(sorted(set(touched))) or "none",
        ),
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
