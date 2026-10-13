"""Build registry entries from Radziszowski's dynamic survey DS1, Table Ia and Table Ib.

  curl -L -o ds1.pdf https://www.combinatorics.org/ojs/index.php/eljc/article/download/DS1/pdf/
  python tools/ingest_ds1.py ds1.pdf [--append data/entries.jsonl]

Needs PyMuPDF (pip install pymupdf); the rest of the registry stays stdlib only. The tables are
read from word coordinates, not from text order: in Table Ia an exact value sits on the row of
its k label, a lower bound just above it and an upper bound just below it. The same layout gives
the references table under Table Ia (top line: lower-bound reference, bottom line: upper-bound
reference, centred: one reference for an exact value). Table Ib lists newer upper bounds
(Angeltveit-McKay); when it improves a Table Ia upper bound, the Table Ia bound goes to
`superseded`. One entry per cell R(k,l), 3 <= k <= l.
"""

import argparse
import hashlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import dump_jsonl, load_jsonl

URL = "https://doi.org/10.37236/21"
PDF_URL = "https://www.combinatorics.org/ojs/index.php/eljc/article/download/DS1/pdf/"
CITATION = "S. P. Radziszowski, Small Ramsey Numbers, Electron. J. Combin. Dynamic Survey DS1, revision #18 (2026-04-24)"
REVISION_DATE = "2026-04-24"
DEFINITION = (
    "R(k,l) is the least n such that every 2-colouring of the edges of the complete graph K_n "
    "contains a K_k in the first colour or a K_l in the second colour."
)
LATEX = r"R(k,l)=\min\{n:\ \forall\,c:E(K_n)\to\{1,2\},\ K_k\subseteq c^{-1}(1)\ \text{or}\ K_l\subseteq c^{-1}(2)\}"


def _words(page):
    return [
        (w[0], w[1], w[2], w[4]) for w in page.get_text("words")
    ]  # x0, y0, x1, text


def _column(x_center, headers):
    return min(headers, key=lambda h: abs(headers[h] - x_center))


def _grid(words, y_from, y_to, header_y, numeric, label_x=110):
    """Map (k, l) -> {'top','mid','bot'} cells for one table block on a page."""
    headers = {
        int(t): (x0 + x1) / 2
        for x0, y, x1, t in words
        if abs(y - header_y) < 2 and t.isdigit()
    }
    rows = {
        int(t): y
        for x0, y, x1, t in words
        if x0 < label_x and y_from < y < y_to and t.isdigit() and 3 <= int(t) <= 10
    }
    cells = {}
    for x0, y, x1, t in words:
        if not (y_from < y < y_to) or x0 < label_x:
            continue
        if numeric and not t.isdigit():
            continue
        k = min(rows, key=lambda r: abs(rows[r] - y))
        dy = y - rows[k]
        if abs(dy) > 9:
            continue
        pos = "mid" if abs(dy) < 2 else ("top" if dy < 0 else "bot")
        l = _column((x0 + x1) / 2, headers)
        cells.setdefault((k, l), {}).setdefault(pos, []).append(t)
    return cells


def parse(pdf_path):
    import pymupdf

    doc = pymupdf.open(pdf_path)
    p6 = _words(doc[5])
    # Table Ia values: header row "l 3 4 5 ... 15" near the top of page 6
    head_y = min(y for x0, y, x1, t in p6 if t == "15")
    caption_y = min(y for x0, y, x1, t in p6 if t == "Ia.")
    values = _grid(p6, head_y + 5, caption_y - 5, head_y, numeric=True)
    # references table: second "15" header on the page, below the caption
    ref_head = min(y for x0, y, x1, t in p6 if t == "15" and y > caption_y)
    ref_end = max(y for x0, y, x1, t in p6 if t == "References")
    refs = _grid(p6, ref_head + 5, ref_end - 3, ref_head, numeric=False)
    p7 = _words(doc[6])
    ib_head = min(y for x0, y, x1, t in p7 if t == "15")
    ib_caption = min(y for x0, y, x1, t in p7 if t == "Ib.")
    ib = _grid(p7, ib_head + 5, ib_caption - 5, ib_head, numeric=True, label_x=140)
    return values, refs, ib


def cells_from(values, refs, ib):
    out = []
    for (k, l), c in sorted(values.items()):
        if l < k:
            continue
        r = refs.get((k, l), {})
        exact = int(c["mid"][0]) if "mid" in c else None
        lower = int(c["top"][0]) if "top" in c else exact
        upper_ia = int(c["bot"][0]) if "bot" in c else exact
        upper_ib = (
            int(ib[(k, l)]["mid"][0]) if (k, l) in ib and "mid" in ib[(k, l)] else None
        )
        upper = upper_ia
        if upper_ib is not None and (upper is None or upper_ib < upper):
            upper = upper_ib
        out.append(
            dict(
                k=k,
                l=l,
                exact=exact,
                lower=lower,
                upper=upper,
                upper_ia=upper_ia,
                upper_ib=upper_ib,
                ref_lower=" ".join(r.get("top", []) or r.get("mid", [])) or None,
                ref_upper=" ".join(r.get("bot", []) or r.get("mid", [])) or None,
            )
        )
    return out


def entry_for(c, eid, sha):
    k, l = c["k"], c["l"]
    name = "R(%d,%d)" % (k, l)
    exact = c["exact"] is not None or (
        c["lower"] is not None and c["lower"] == c["upper"]
    )
    if exact:
        value, kind = c["exact"] if c["exact"] is not None else c["lower"], "exact"
    else:
        value = "%s <= %s <= %s" % (
            c["lower"] if c["lower"] is not None else "?",
            name,
            c["upper"] if c["upper"] is not None else "?",
        )
        kind = "bound"
    superseded = []
    if (
        c["upper_ib"] is not None
        and c["upper_ia"] is not None
        and c["upper_ib"] < c["upper_ia"]
    ):
        superseded.append(
            {
                "value": "%s <= %d" % (name, c["upper_ia"]),
                "source": "DS1 Table Ia upper bound (%s)"
                % (c["ref_upper"] or "no reference listed"),
                "url": URL,
                "date": None,
            }
        )
    refs = "lower bound: %s; upper bound: %s" % (
        c["ref_lower"] or "none listed",
        (
            "Table Ib (Angeltveit-McKay: AnM2/AnM3/AnM4)"
            if superseded
            else c["ref_upper"]
        )
        or "none listed",
    )
    if exact:
        refs = "exact value; references %s" % (
            (c["ref_lower"] or "none listed (classical)")
            if c["ref_lower"] == c["ref_upper"]
            else "%s (lower) / %s (upper)" % (c["ref_lower"], c["ref_upper"])
        )
    return {
        "id": eid,
        "problem_family": "Ramsey theory",
        "variant_name": "Classical two-colour Ramsey number %s" % name,
        "definition": {
            "text": DEFINITION.replace("K_k", "K_%d" % k)
            .replace("K_l", "K_%d" % l)
            .replace("R(k,l)", name),
            "latex": LATEX.replace("R(k,l)", name)
            .replace("K_k", "K_{%d}" % k)
            .replace("K_l", "K_{%d}" % l),
            "status": "curated",
        },
        "domain": "2-colourings of the edges of complete graphs",
        "direction": "unstated",
        "units_or_normalisation": "number of vertices; a lower bound L means R > L-1 is shown by a colouring of K_{L-1}",
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
            "citation": CITATION
            + ", Table I"
            + ("a and Table Ib" if superseded else "a"),
            "url": URL,
            "date": REVISION_DATE,
            "refereed": True,
        },
        "superseded": superseded,
        "aliases": [{"scheme": "DS1", "id": name}],
        "status": "current",
        "last_checked": REVISION_DATE,
        "conflation_note": None,
        "notes": "Parsed from the DS1 PDF (sha256 %s) by tools/ingest_ds1.py; %s. Table Ib bounds are reported in the survey "
        "as obtained by large computations and partly unpublished in 2024."
        % (sha, refs),
        "provenance": {
            "setter_kind": "unknown",
            "literature_status": "unknown",
            "first_public_date": None,
            "platform_or_paper": "%s ; survey references %s" % (URL, refs),
            "basis": "DS1 lists references per bound, not whether a bound was found with machine search; per-paper provenance is to be filled",
        },
        "fidelity": {
            "statement_audit": "self",
            "audit_note": "Standard definition, transcribed by the maintainers; matches DS1 section 2.1.",
        },
        "feasibility": None,
        "_exact": exact,
    }


def build(pdf_path, start_id):
    with open(pdf_path, "rb") as fh:
        sha = hashlib.sha256(fh.read()).hexdigest()
    cells = cells_from(*parse(pdf_path))
    out = []
    for i, c in enumerate(cells):
        e = entry_for(c, "EV-%06d" % (start_id + i), sha)
        e.pop("_exact")
        out.append(e)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument(
        "--append", help="entries.jsonl to append to (ids continue from its last id)"
    )
    a = ap.parse_args(argv)
    existing = load_jsonl(a.append) if a.append else []
    start = max([int(e["id"][3:]) for e in existing] or [0]) + 1
    taken = {(x["scheme"], x["id"]) for e in existing for x in e["aliases"]}
    new = [
        e for e in build(a.pdf, start) if ("DS1", e["aliases"][0]["id"]) not in taken
    ]
    for i, e in enumerate(new):
        e["id"] = "EV-%06d" % (start + i)
    if a.append:
        with open(a.append, "a", encoding="utf-8", newline="\n") as fh:
            fh.write(dump_jsonl(new))
    else:
        sys.stdout.write(dump_jsonl(new))
    print(
        "%d DS1 entries (%d exact)"
        % (len(new), sum(e["value_kind"] == "exact" for e in new)),
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
