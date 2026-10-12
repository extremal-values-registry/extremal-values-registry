"""Propose registry updates from a dated rows CSV in the freshcheck row format.

  python tools/check_freshness.py rows_YYYY-MM-DD.csv [--entries data/entries.jsonl] [--apply]

Rows are matched to entries by (benchmark, problem_id) against entry aliases, or by an
EV-NNNNNN id in problem_id. For each matched row, last_checked becomes the row's
search_date (if later). A STALE row whose source_kind is primary or validator, with a
non-empty quote in notes and a better_value strictly better than the entry's current value,
becomes a proposed supersession: the old value moves to superseded[] and the entry gets
the new value and source. Anything else that claims STALE is reported, not applied.

The tool always prints a unified diff of entries.jsonl and writes nothing unless --apply is
given. Exit 0 = no proposed change, 2 = changes proposed (or applied), 1 = input error.
"""

import argparse
import copy
import csv
import difflib
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ENTRIES, dump_jsonl, load_jsonl, num, strictly_better

COLUMNS = [
    "benchmark",
    "problem_id",
    "pinned_value",
    "pinned_commit",
    "direction",
    "search_date",
    "searcher",
    "verdict",
    "better_value",
    "source",
    "source_date",
    "source_kind",
    "queries_run",
    "notes",
]
SCHEME_OF = {
    "horizonmath": "HorizonMath",
    "optimization constants in mathematics": "OptimizationConstants",
    "optimizationconstants": "OptimizationConstants",
    "einsteinarena": "EinsteinArena",
    "alphaevolve_results_notebook": "AlphaEvolve-notebook",
    "alphaevolve-notebook": "AlphaEvolve-notebook",
    "alphaevolve_v2_paper": "AlphaEvolve-v2-paper",
    "alphaevolve-v2-paper": "AlphaEvolve-v2-paper",
}


def read_rows(path):
    with open(path, encoding="utf-8", newline="") as fh:
        r = csv.DictReader(fh)
        missing = [c for c in COLUMNS if c not in (r.fieldnames or [])]
        if missing:
            raise ValueError("rows file lacks columns: %s" % ", ".join(missing))
        return list(r)


def find_entry(entries, row):
    pid = row["problem_id"].strip()
    if re.fullmatch(r"EV-\d{6}", pid):
        return next((e for e in entries if e["id"] == pid), None)
    scheme = SCHEME_OF.get(row["benchmark"].strip().lower(), row["benchmark"].strip())
    for e in entries:
        for a in e["aliases"]:
            ids = {a["id"], a["id"] + "|" + a["side"]} if a.get("side") else {a["id"]}
            if a["scheme"] == scheme and pid in ids:
                return e
    return None


def url_of(source):
    m = re.search(r"https?://\S+", source or "")
    if m:
        return m.group(0).rstrip(";,)")
    m = re.search(r"arXiv:?\s*(\d{4}\.\d{4,5})", source or "", re.IGNORECASE)
    return "https://arxiv.org/abs/" + m.group(1) if m else None


def propose(entries, rows):
    new = copy.deepcopy(entries)
    report = []
    for row in rows:
        e = find_entry(new, row)
        if e is None:
            report.append("unmatched: %s %s" % (row["benchmark"], row["problem_id"]))
            continue
        sd = row["search_date"].strip()
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", sd) and sd > e["last_checked"]:
            e["last_checked"] = sd
        if row["verdict"].strip().upper() != "STALE":
            continue
        kind = row["source_kind"].strip().lower()
        bv = row["better_value"].strip()
        if kind not in ("primary", "validator") or not row["notes"].strip():
            report.append(
                "%s: STALE row not applied (needs primary/validator source and a quote)"
                % e["id"]
            )
            continue
        if not strictly_better(e["direction"], bv, e["current_value"]):
            report.append(
                "%s: STALE row not applied (%s is not strictly better than %s, direction %s)"
                % (e["id"], bv, e["current_value"], e["direction"])
            )
            continue
        e["superseded"].append(
            dict(
                value=e["current_value"],
                source=e["source"]["citation"],
                url=e["source"]["url"],
                date=e["source"]["date"],
            )
        )
        v = num(bv)
        e["current_value"] = (
            int(v)
            if v is not None and v.is_integer() and re.fullmatch(r"[-+]?\d+", bv)
            else v
        )
        e["value_kind"] = "record" if kind == "validator" else "bound"
        e["source"] = dict(
            citation=row["source"].strip() or None,
            url=url_of(row["source"]),
            date=row["source_date"].strip() or None,
            refereed=False,
        )
        e["certificate"] = dict(
            file=None,
            sha256=None,
            verifier_command=None,
            verifier_kind="external",
            verified_date=None,
            value_pattern=None,
            tolerance=None,
        )
        e["notes"] = (
            "Supersession proposed from rows of %s: %s. "
            % (sd, row["notes"].strip()[:400])
        ) + (e["notes"] or "")
        report.append(
            "%s: supersede %s -> %s"
            % (e["id"], e["superseded"][-1]["value"], e["current_value"])
        )
    return new, report


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("rows")
    ap.add_argument("--entries", default=ENTRIES)
    ap.add_argument(
        "--apply",
        action="store_true",
        help="write the proposed changes (prints the diff first)",
    )
    a = ap.parse_args(argv)
    try:
        rows = read_rows(a.rows)
    except (OSError, ValueError) as exc:
        print("error:", exc, file=sys.stderr)
        return 1
    entries = load_jsonl(a.entries)
    new, report = propose(entries, rows)
    before, after = dump_jsonl(entries), dump_jsonl(new)
    diff = list(
        difflib.unified_diff(
            before.splitlines(True),
            after.splitlines(True),
            fromfile=a.entries,
            tofile=a.entries + " (proposed)",
        )
    )
    for line in report:
        print("#", line)
    sys.stdout.write("".join(diff))
    if not diff:
        print("# no changes proposed")
        return 0
    if a.apply:
        with open(a.entries, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(after)
        print("# applied to", a.entries)
    else:
        print("# not written (pass --apply to write)")
    return 2


if __name__ == "__main__":
    sys.exit(main())
