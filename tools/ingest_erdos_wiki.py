"""Build registry entries from the frozen 'AI contributions to Erdős problems' wiki page.

  git clone https://github.com/teorth/erdosproblems.wiki.git wiki
  git -C wiki show HEAD:AI-contributions-to-Erdős-problems.md > ai.md
  python tools/ingest_erdos_wiki.py ai.md --commit <wiki sha> [--append data/entries.jsonl]

One entry per problem number. The value is a status: "resolved" when some row records a full
resolution (green), otherwise "open". Provenance follows the wiki's section placement
(1(a) AI standalone: literature unknown; 1(b) alongside literature: found_after; 1(c) building on
literature: known_before; 1(d) with humans: human_ai; section 2: AI secondary, the result is
human and, for formalisation or rewriting of an earlier proof, known_before). Every wiki row for the problem is kept in provenance.records with its date,
colour, outcome and the number of AI systems involved; product names are replaced by "AI system".
Stdlib only.
"""

import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import dump_jsonl, load_jsonl

WIKI_URL = "https://github.com/teorth/erdosproblems/wiki/AI-contributions-to-Erd%C5%91s-problems"
FROZEN = "2026-06-30"
COLOUR = {
    "\U0001f7e2": "green",
    "\U0001f7e1": "yellow",
    "\U0001f534": "red",
    "⚪": "white",
}
RANK = {"green": 3, "yellow": 2, "red": 1, "white": 0, None: -1}
STATE = {
    "green": "full",
    "yellow": "partial",
    "red": "incorrect",
    "white": "unverified",
    None: "not_applicable",
}
SECTION = {
    "1(a)": ("ai_system", "unknown"),
    "1(b)": ("ai_system", "found_after"),
    "1(c)": ("ai_system", "known_before"),
    "1(d)": ("human_ai", "unknown"),
    "2(a)": ("human", "known_before"),
    "2(b)": ("human", "known_before"),
    "2(c)": ("human", "known_before"),
    "2(d)": ("human", "unknown"),
}
PARTIAL = re.compile(r"(?i)variant|extension|part\b|conditional")
MONTHS = {
    m: i + 1
    for i, m in enumerate(
        [
            "Jan",
            "Feb",
            "Mar",
            "Apr",
            "May",
            "Jun",
            "Jul",
            "Aug",
            "Sep",
            "Oct",
            "Nov",
            "Dec",
        ]
    )
}


def parse_date(s):
    """First date in a cell such as '24 Jan, 2026', '23 Mar-4 Apr, 2026' or 'Dec, 2025'."""
    years = re.findall(r"(\d{4})", s or "")
    m = re.search(
        r"(?:(\d{1,2})\s+)?(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)", s or ""
    )
    if not years:
        return None
    if not m:
        return years[0]
    out = "%s-%02d" % (years[0], MONTHS[m.group(2)])
    return out + ("-%02d" % int(m.group(1)) if m.group(1) else "")


def colour_of(cell):
    for sym, name in COLOUR.items():
        if sym in (cell or ""):
            return name
    return None


def parse_rows(text):
    """Yield dicts (problem, section, columns...) for every table row of the page."""
    section, header = None, None
    for line in text.splitlines():
        h = re.match(r"^###\s+(\d\([a-d]\))", line)
        if h:
            section, header = h.group(1), None
            continue
        if not line.startswith("|") or section is None:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if cells and cells[0] == "Problem":
            header = cells
            continue
        if header is None or set("".join(cells)) <= set("- :"):
            continue
        m = re.match(r"\[\[(\d+)\]\]", cells[0])
        if not m:
            continue
        row = dict(zip(header, cells + [""] * (len(header) - len(cells))))
        row["problem"] = int(m.group(1))
        row["section"] = section
        yield row


def ai_names(rows):
    """Every system named in an 'AI systems' cell of the page, longest first."""
    names = {n.strip() for r in rows for n in (r.get("AI systems") or "").split(",")}
    return sorted((n for n in names if len(n) > 2), key=len, reverse=True)


def redact(text, names):
    """Replace system names by 'AI system'; the registry records who set a value, not which product."""
    if not text:
        return text, False
    out = text
    for n in names:
        out = out.replace(n, "AI system")
    return out, out != text


def record_of(row, names):
    raw = (
        row.get("Outcome")
        or row.get("Computation")
        or row.get("Argument to rewrite")
        or row.get("Proof to formalize")
    )
    outcome, ai_named = redact(raw, names)
    rec = {
        "section": row["section"],
        "date": parse_date(row.get("Date")),
        "outcome": outcome or None,
        "colour": colour_of(raw),
        "ai_systems": len([n for n in (row.get("AI systems") or "").split(",") if n.strip()]),
    }
    if row.get("Literature"):
        rec["literature"] = redact(row["Literature"], names)[0]
    rec["_ai_proof"] = ai_named and row["section"] in ("2(b)", "2(c)")
    return rec


def full_resolution(rec):
    """Green, and about the problem itself rather than a variant, an extension or one part."""
    return rec["colour"] == "green" and not PARTIAL.search(rec["outcome"] or "")


def setter_of(rec):
    if rec["_ai_proof"]:
        # the proof being formalised or rewritten is itself an AI proof
        return "unknown", "unknown"
    return SECTION[rec["section"]]


def build(text, start_id, commit, checked):
    rows = list(parse_rows(text))
    names = ai_names(rows)
    by_problem = {}
    for row in rows:
        by_problem.setdefault(row["problem"], []).append(record_of(row, names))
    entries = []
    for i, (n, recs) in enumerate(sorted(by_problem.items())):
        coloured = [r for r in recs if r["colour"] is not None]
        sect1 = [r for r in coloured if r["section"].startswith("1")]
        pool = sect1 or coloured
        best = None
        if pool:
            top = max(RANK[r["colour"]] for r in pool)
            # the earliest row with the best colour (section 1 first) decides the provenance
            best = min(
                (r for r in pool if RANK[r["colour"]] == top),
                key=lambda r: r["date"] or "9999",
            )
        decider = best or min(recs, key=lambda r: r["date"] or "9999")
        setter, lit = setter_of(decider)
        resolved = any(full_resolution(r) for r in recs)
        colours = [r["colour"] for r in recs if r["colour"]]
        dates = sorted(r["date"] for r in recs if r["date"])
        lean = any("Lean" in (r["outcome"] or "") for r in recs) or any(
            r["section"] == "2(b)" for r in recs
        )
        url = "https://www.erdosproblems.com/%d" % n
        entries.append(
            {
                "id": "EV-%06d" % (start_id + i),
                "problem_family": "Erdős problems",
                "variant_name": "Erdős problem #%d (resolution status, AI-contributions wiki)"
                % n,
                "definition": {
                    "text": "Erdős problem #%d exactly as stated at %s. The registry records whether it is resolved, not a numeric value."
                    % (n, url),
                    "latex": "",
                    "status": "source_label",
                },
                "domain": "statement at erdosproblems.com",
                "direction": "unstated",
                "units_or_normalisation": "status: resolved (a full resolution is recorded on the wiki) | open (none recorded)",
                "current_value": "resolved" if resolved else "open",
                "value_kind": "status",
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
                    "citation": "AI contributions to Erdős problems wiki (frozen %s, wiki commit %s), problem %d"
                    % (FROZEN, commit[:7], n),
                    "url": WIKI_URL,
                    "date": FROZEN,
                    "refereed": False,
                },
                "superseded": [],
                "aliases": [{"scheme": "ErdosProblems", "id": str(n)}],
                "status": "current"
                if any(c != "white" for c in colours) or not colours
                else "unclear",
                "last_checked": checked,
                "conflation_note": None,
                "notes": "Status is the wiki's view as of %s, not a check of erdosproblems.com. 'open' means no full "
                "resolution is recorded on the wiki; it may still be solved elsewhere. %d wiki row(s)."
                % (FROZEN, len(recs)),
                "provenance": {
                    "setter_kind": setter,
                    "literature_status": lit,
                    "first_public_date": dates[0] if dates else None,
                    "platform_or_paper": "%s ; wiki section %s"
                    % (url, decider["section"]),
                    "verification_state": STATE[best["colour"] if best else None],
                    "basis": "wiki section placement of the earliest row with the best colour (section 1 before section 2)",
                    "records": [{k: v for k, v in r.items() if not k.startswith("_")} for r in recs],
                },
                "fidelity": {
                    "statement_audit": "none",
                    "audit_note": "A Lean formalisation is reported on the wiki for this problem; its agreement with the "
                    "erdosproblems.com statement has not been audited here.",
                }
                if lean
                else None,
                "feasibility": None,
            }
        )
    return entries


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("page", help="the wiki page as markdown")
    ap.add_argument(
        "--commit", required=True, help="wiki git commit the page was read at"
    )
    ap.add_argument("--checked", default=FROZEN)
    ap.add_argument(
        "--append", help="entries.jsonl to append to (ids continue from its last id)"
    )
    a = ap.parse_args(argv)
    with open(a.page, encoding="utf-8") as fh:
        text = fh.read()
    existing = load_jsonl(a.append) if a.append else []
    start = max([int(e["id"][3:]) for e in existing] or [0]) + 1
    taken = {(x["scheme"], x["id"]) for e in existing for x in e["aliases"]}
    new = [
        e
        for e in build(text, start, a.commit, a.checked)
        if ("ErdosProblems", e["aliases"][0]["id"]) not in taken
    ]
    for i, e in enumerate(new):
        e["id"] = "EV-%06d" % (start + i)
    if a.append:
        with open(a.append, "a", encoding="utf-8", newline="\n") as fh:
            fh.write(dump_jsonl(new))
    else:
        sys.stdout.write(dump_jsonl(new))
    print("%d Erdős entries" % len(new), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
