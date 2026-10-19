"""Export the registry as CSV and a static HTML index (one page per entry).

  python tools/export.py [--entries data/entries.jsonl] [--out dist]

Writes <out>/entries.csv, <out>/index.html, <out>/entries/EV-NNNNNN.html and the
shields.io endpoint badges under <out>/badge/ (see tools/badges.py). Stdlib only.
"""

import argparse
import csv
import html
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from badges import write_badges
from common import ENTRIES, ROOT, load_jsonl

CSV_COLUMNS = [
    "id",
    "problem_family",
    "variant_name",
    "direction",
    "current_value",
    "value_kind",
    "status",
    "units_or_normalisation",
    "source_citation",
    "source_url",
    "source_date",
    "refereed",
    "certificate_file",
    "verifier_kind",
    "superseded_values",
    "aliases",
    "last_checked",
    "setter_kind",
    "literature_status",
    "first_public_date",
    "statement_audit",
    "feasibility",
]

STYLE = """
:root{--bg:#fbfaf7;--fg:#1d1d1f;--muted:#5f5f66;--line:#e2e0da;--accent:#1f4f8f}
@media (prefers-color-scheme:dark){:root{--bg:#141416;--fg:#ececef;--muted:#a3a3ad;--line:#2c2c31;--accent:#8db4ff}}
body{background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,sans-serif;margin:0 auto;max-width:960px;padding:16px}
a{color:var(--accent)}table{border-collapse:collapse;width:100%}th,td{border-bottom:1px solid var(--line);
padding:4px 6px;text-align:left;vertical-align:top}th{color:var(--muted);font-weight:600}
code,pre{font-family:ui-monospace,monospace;font-size:13px;white-space:pre-wrap;word-break:break-word}
.muted{color:var(--muted)}.wrap{overflow-x:auto}
"""


def esc(x):
    return html.escape("" if x is None else str(x))


def row_for_csv(e):
    return {
        "id": e["id"],
        "problem_family": e["problem_family"],
        "variant_name": e["variant_name"],
        "direction": e["direction"],
        "current_value": "" if e["current_value"] is None else e["current_value"],
        "value_kind": e["value_kind"],
        "status": e["status"],
        "units_or_normalisation": e["units_or_normalisation"],
        "source_citation": e["source"]["citation"] or "",
        "source_url": e["source"]["url"] or "",
        "source_date": e["source"]["date"] or "",
        "refereed": e["source"]["refereed"],
        "certificate_file": e["certificate"]["file"] or "",
        "verifier_kind": e["certificate"]["verifier_kind"],
        "superseded_values": " ; ".join(str(s["value"]) for s in e["superseded"]),
        "aliases": " ; ".join(
            "%s:%s%s" % (a["scheme"], a["id"], "|" + a["side"] if a.get("side") else "")
            for a in e["aliases"]
        ),
        "last_checked": e["last_checked"],
        "setter_kind": e["provenance"]["setter_kind"],
        "literature_status": e["provenance"]["literature_status"],
        "first_public_date": e["provenance"]["first_public_date"] or "",
        "statement_audit": (e["fidelity"] or {}).get("statement_audit", ""),
        "feasibility": feasibility_label(e),
    }


def feasibility_label(e):
    f = e["feasibility"]
    if not f:
        return ""
    return f.get("result") or ("checked" if f["definition_checked"] else "not_checked")


def provenance_html(e):
    p = e["provenance"]
    rows = "".join(
        "<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>"
        % (esc(r["section"]), esc(r["date"]), esc(r.get("ai_systems")), esc(r["outcome"]))
        for r in p.get("records", [])
    )
    out = "<p>Set by: <b>%s</b>. Literature: %s. First public: %s.<br>Where: %s</p>" % (
        esc(p["setter_kind"]),
        esc(p["literature_status"]),
        esc(p["first_public_date"]),
        esc(p["platform_or_paper"]),
    )
    if p.get("verification_state"):
        out += "<p>Verification state (source's colour): %s</p>" % esc(p["verification_state"])
    if p.get("basis"):
        out += "<p class=muted>Basis: %s</p>" % esc(p["basis"])
    if rows:
        out += (
            "<div class=wrap><table><tr><th>section</th><th>date</th><th>AI systems (count)</th><th>outcome</th></tr>%s</table></div>"
            % rows
        )
    return out


def fidelity_html(e):
    f = e["fidelity"]
    if not f:
        return "<p class=muted>No formal statement recorded for this entry.</p>"
    return "<p>Statement audit: <b>%s</b>. %s</p>" % (esc(f["statement_audit"]), esc(f["audit_note"]))


def feasibility_html(e):
    f = e["feasibility"]
    if not f:
        return "<p class=muted>Not applicable or not checked.</p>"
    out = "<p>Definition checked: <b>%s</b>; result: <b>%s</b>" % (
        "yes" if f["definition_checked"] else "no",
        esc(f.get("result", "")),
    )
    if f.get("records_checked") is not None:
        out += "; %d records checked, %d infeasible, %d not reproduced" % (
            f["records_checked"],
            f.get("records_infeasible", 0),
            f.get("records_not_reproduced", 0),
        )
    out += ".</p>"
    if f.get("check_source"):
        out += "<p class=muted>Source: %s</p>" % esc(f["check_source"])
    if f.get("note"):
        out += "<p class=muted>%s</p>" % esc(f["note"])
    return out


def page(title, body):
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        "<title>%s</title><style>%s</style></head><body>%s</body></html>\n"
        % (esc(title), STYLE, body)
    )


def entry_page(e):
    link = lambda u: '<a href="%s">%s</a>' % (esc(u), esc(u)) if u else ""
    chain = "".join(
        "<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>"
        % (esc(s["value"]), esc(s["source"]), link(s["url"]), esc(s["date"]))
        for s in e["superseded"]
    )
    aliases = "".join(
        "<li>%s: <code>%s</code>%s</li>"
        % (
            esc(a["scheme"]),
            esc(a["id"]),
            esc(" (" + a["side"] + ")") if a.get("side") else "",
        )
        for a in e["aliases"]
    )
    c = e["certificate"]
    cert = (
        "<p>File <code>%s</code> (sha256 <code>%s</code>)<br>Verifier (%s): <code>%s</code>, verified %s</p>"
        % (
            esc(c["file"]),
            esc(c["sha256"]),
            esc(c["verifier_kind"]),
            esc(c["verifier_command"]),
            esc(c["verified_date"]),
        )
        if c["file"]
        else "<p class=muted>No certificate in this registry; the value rests on the cited source.</p>"
    )
    body = [
        '<p><a href="../index.html">All entries</a></p>',
        "<h1>%s</h1><p class=muted>%s &middot; %s &middot; status %s</p>"
        % (
            esc(e["id"]),
            esc(e["variant_name"]),
            esc(e["problem_family"]),
            esc(e["status"]),
        ),
        "<h2>Definition</h2><p>%s</p>" % esc(e["definition"]["text"]),
        "<pre>%s</pre>" % esc(e["definition"]["latex"])
        if e["definition"]["latex"]
        else "",
        "<p class=muted>Domain: %s. Normalisation: %s. Direction: %s.</p>"
        % (esc(e["domain"]), esc(e["units_or_normalisation"]), esc(e["direction"])),
        "<h2>Current value</h2><p><b>%s</b> (%s)</p>"
        % (esc(e["current_value"]), esc(e["value_kind"])),
        "<p>Source: %s %s %s%s</p>"
        % (
            esc(e["source"]["citation"]),
            link(e["source"]["url"]),
            esc(e["source"]["date"]),
            " (refereed)" if e["source"]["refereed"] else "",
        ),
        "<h2>Certificate</h2>" + cert,
        "<h2>Supersession chain</h2>"
        + (
            "<div class=wrap><table><tr><th>value</th><th>source</th><th>url</th><th>date</th></tr>%s</table></div>"
            % chain
            if chain
            else "<p class=muted>None recorded.</p>"
        ),
        "<h2>Provenance</h2>" + provenance_html(e),
        "<h2>Statement fidelity</h2>" + fidelity_html(e),
        "<h2>Definition-level feasibility</h2>" + feasibility_html(e),
        "<h2>Aliases</h2><ul>%s</ul>" % aliases,
        "<h2>Conflation note</h2><p>%s</p>" % esc(e["conflation_note"])
        if e["conflation_note"]
        else "",
        "<h2>Notes</h2><p class=muted>%s</p>" % esc(e["notes"]) if e["notes"] else "",
        "<p class=muted>Last checked %s.</p>" % esc(e["last_checked"]),
    ]
    return page("%s %s" % (e["id"], e["variant_name"]), "".join(body))


def export(entries, out):
    os.makedirs(os.path.join(out, "entries"), exist_ok=True)
    with open(
        os.path.join(out, "entries.csv"), "w", encoding="utf-8", newline=""
    ) as fh:
        w = csv.DictWriter(fh, fieldnames=CSV_COLUMNS, lineterminator="\n")  # LF, as .gitattributes stores it
        w.writeheader()
        for e in entries:
            w.writerow(row_for_csv(e))
    rows = "".join(
        '<tr><td><a href="entries/%s.html">%s</a></td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>'
        % (
            esc(e["id"]),
            esc(e["id"]),
            esc(e["variant_name"]),
            esc(e["direction"]),
            esc(e["current_value"]),
            esc(e["status"]),
            esc(e["provenance"]["setter_kind"]),
            esc(feasibility_label(e)),
        )
        for e in entries
    )
    with open(os.path.join(out, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(
            page(
                "Extremal values registry",
                "<h1>Extremal values registry</h1><p class=muted>%d entries. "
                "An entry is a fact only when its verifier passes.</p><div class=wrap><table><tr><th>id</th>"
                "<th>variant</th><th>dir</th><th>value</th><th>status</th><th>set by</th><th>feasibility</th></tr>%s</table></div>"
                % (len(entries), rows),
            )
        )
    for e in entries:
        with open(
            os.path.join(out, "entries", e["id"] + ".html"), "w", encoding="utf-8"
        ) as fh:
            fh.write(entry_page(e))
    write_badges(entries, out)
    return len(entries)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--entries", default=ENTRIES)
    ap.add_argument("--out", default=os.path.join(ROOT, "dist"))
    a = ap.parse_args(argv)
    n = export(load_jsonl(a.entries), a.out)
    print("exported %d entries to %s" % (n, a.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
