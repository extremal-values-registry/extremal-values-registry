"""Generate shields.io endpoint badges from the registry.

  python tools/badges.py [--entries data/entries.jsonl] [--out docs]

Writes <out>/badge/<id>.json per entry, <out>/badge/table/<slug>.json per audited
benchmark table, <out>/badge/source/<slug>.json per ingested source table,
<out>/badge/provenance.json and <out>/badge/registry.json. Embed with
https://img.shields.io/endpoint?url=<PAGES_BASE>/badge/<id>.json. Stdlib only.
"""

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ENTRIES, ROOT, load_jsonl

COLORS = {"current": "green", "unclear": "yellow", "malformed": "red"}


def badge(label, message, color):
    return {"schemaVersion": 1, "label": label, "message": message, "color": color}


def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


SOURCE_SCHEMES = {"ErdosProblems": "erdos-ai-contributions-wiki", "DS1": "ds1-small-ramsey-numbers"}


def entry_badge(e):
    f = e.get("feasibility") or {}
    bad = f.get("result") in ("infeasible", "score_not_reproduced")
    return badge(
        e["id"],
        "%s · %s%s" % (e["status"], e["last_checked"], " · " + f["result"].replace("_", " ") if bad else ""),
        "red" if bad else COLORS.get(e["status"], "lightgrey"),
    )


def source_badges(entries):
    """One badge per ingested source table: entry count and how many are exact or resolved."""
    out = {}
    for scheme, name in SOURCE_SCHEMES.items():
        es = [e for e in entries if any(a["scheme"] == scheme for a in e["aliases"])]
        if not es:
            continue
        settled = sum(1 for e in es if e["value_kind"] == "exact" or e["current_value"] == "resolved")
        word = "resolved" if scheme == "ErdosProblems" else "exact"
        out[name] = badge(name, "%d entries · %d %s" % (len(es), settled, word), "blue")
    return out


def provenance_badge(entries):
    ai = sum(1 for e in entries if e.get("provenance", {}).get("setter_kind") in ("ai_system", "human_ai"))
    checked = sum(1 for e in entries if (e.get("feasibility") or {}).get("definition_checked"))
    return badge("provenance", "%d AI-involved · %d definition-checked" % (ai, checked), "blue")


def table_badges(entries):
    tables = {}
    for e in entries:
        for a in e["aliases"]:
            t = a.get("audit_table")
            if t:
                tables.setdefault(t, {})[e["id"]] = e
    out = {}
    for t, members in sorted(tables.items()):
        es = list(members.values())
        n = sum(1 for e in es if e["status"] == "current")
        date = max(e["last_checked"] for e in es)
        color = "green" if n == len(es) else ("red" if n * 2 < len(es) else "yellow")
        out[slug(t)] = badge(t, "%d/%d current · %s" % (n, len(es), date), color)
    return out


def write_badges(entries, out):
    d = os.path.join(out, "badge")
    os.makedirs(os.path.join(d, "table"), exist_ok=True)

    def dump(path, obj):
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(obj, fh, ensure_ascii=False)
            fh.write("\n")

    for e in entries:
        dump(os.path.join(d, e["id"] + ".json"), entry_badge(e))
    tables = table_badges(entries)
    for s, b in tables.items():
        dump(os.path.join(d, "table", s + ".json"), b)
    sources = source_badges(entries)
    if sources:
        os.makedirs(os.path.join(d, "source"), exist_ok=True)
    for s, b in sources.items():
        dump(os.path.join(d, "source", s + ".json"), b)
    dump(os.path.join(d, "provenance.json"), provenance_badge(entries))
    date = max(e["last_checked"] for e in entries) if entries else ""
    dump(
        os.path.join(d, "registry.json"),
        badge("registry", "%d entries · %s" % (len(entries), date), "blue"),
    )
    return len(entries), len(tables)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--entries", default=ENTRIES)
    ap.add_argument("--out", default=os.path.join(ROOT, "docs"))
    a = ap.parse_args(argv)
    n, t = write_badges(load_jsonl(a.entries), a.out)
    print("wrote %d entry badges and %d table badges to %s" % (n, t, os.path.join(a.out, "badge")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
