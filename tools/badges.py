"""Generate shields.io endpoint badges from the registry.

  python tools/badges.py [--entries data/entries.jsonl] [--out docs]

Writes <out>/badge/<id>.json per entry, <out>/badge/table/<slug>.json per audited
benchmark table, and <out>/badge/registry.json. Embed with
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


def entry_badge(e):
    return badge(
        e["id"],
        "%s · %s" % (e["status"], e["last_checked"]),
        COLORS.get(e["status"], "lightgrey"),
    )


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
