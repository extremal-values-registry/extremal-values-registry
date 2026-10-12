"""Two-pass literature check for changed entries (the replicate step of a pull request).

  python tools/literature_check.py --ids EV-000004 [EV-...] [--entries data/entries.jsonl]
                                   [--out rows_YYYY-MM-DD.csv] [--date YYYY-MM-DD]

Two independent passes over two free scholarly indexes, each with its own query built from
the entry's variant name and aliases:
  pass 1: OpenAlex works search      (https://api.openalex.org/works)
  pass 2: arXiv API                  (http://export.arxiv.org/api/query)
Neither costs money. The key comes from the environment variable LITERATURE_KEY (a
repository secret in CI: an OpenAlex API key or contact address for the polite pool). When
it is absent the script makes no request, prints "needs-literature-check" and exits 3, and
the workflow labels the pull request instead of failing it.

A pass can only find candidates. It never writes STALE: a supersession needs a verbatim
quote from a primary source that a person (or agent) opened, recorded in a rows file and
applied with tools/check_freshness.py. The output is a rows CSV in the freshcheck format:
  CURRENT  both passes returned no work dated after the entry's source date
  UNCLEAR  at least one candidate; the titles and links are in notes for a reviewer
Exit 0 = all CURRENT, 2 = candidates to read, 3 = no key, 1 = input error.
"""

import argparse
import csv
import datetime
import json
import os
import re
import sys
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_freshness import COLUMNS
from common import ENTRIES, load_jsonl

KEY_ENV = "LITERATURE_KEY"
NEEDS_LABEL = "needs-literature-check"
UA = "extremal-values-registry-literature-check/0 (stdlib urllib)"


def _get(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def query_terms(entry):
    words = re.sub(r"[^A-Za-z0-9' -]+", " ", entry["variant_name"]).split()
    return " ".join(words[:8])


def pass_openalex(entry, key, since, get=_get):
    params = {"search": query_terms(entry), "per-page": "25"}
    if since:
        params["filter"] = "from_publication_date:%s" % since
    params["api_key" if "@" not in key else "mailto"] = key
    data = json.loads(
        get("https://api.openalex.org/works?" + urllib.parse.urlencode(params))
    )
    return [
        {
            "title": w.get("display_name") or "",
            "url": w.get("doi") or w.get("id"),
            "date": w.get("publication_date"),
        }
        for w in data.get("results", [])
    ]


def pass_arxiv(entry, key, since, get=_get):
    q = "all:" + " AND all:".join(query_terms(entry).split()[:5])
    url = "http://export.arxiv.org/api/query?" + urllib.parse.urlencode(
        {"search_query": q, "max_results": "25", "sortBy": "submittedDate"}
    )
    xml = get(url)
    hits = []
    for block in re.findall(r"<entry>(.*?)</entry>", xml, re.DOTALL):
        title = re.search(r"<title>(.*?)</title>", block, re.DOTALL)
        link = re.search(r"<id>(.*?)</id>", block)
        date = re.search(r"<published>(\d{4}-\d{2}-\d{2})", block)
        d = date.group(1) if date else None
        if since and d and d <= since:
            continue
        hits.append(
            {
                "title": " ".join((title.group(1) if title else "").split()),
                "url": link and link.group(1),
                "date": d,
            }
        )
    return hits


def check_entry(entry, key, date, get=_get):
    since = entry["source"].get("date")
    p1 = pass_openalex(entry, key, since, get)
    p2 = pass_arxiv(entry, key, since, get)
    hits = p1 + p2
    alias = (
        entry["aliases"][0]
        if entry["aliases"]
        else {"scheme": "registry", "id": entry["id"]}
    )
    notes = "; ".join(
        "%s <%s> %s" % (h["title"][:120], h["url"], h["date"]) for h in hits[:10]
    )
    return {
        "benchmark": "registry",
        "problem_id": entry["id"],
        "pinned_value": entry["current_value"],
        "pinned_commit": "",
        "direction": entry["direction"],
        "search_date": date,
        "searcher": "pass1-openalex+pass2-arxiv",
        "verdict": "UNCLEAR" if hits else "CURRENT",
        "better_value": "",
        "source": "",
        "source_date": "",
        "source_kind": "",
        "queries_run": "%s | alias %s:%s | %d+%d hits"
        % (query_terms(entry), alias["scheme"], alias["id"], len(p1), len(p2)),
        "notes": ("candidates to open: " + notes)
        if hits
        else "no work after %s in either pass" % since,
    }


def main(argv=None, get=_get, env=None):
    env = os.environ if env is None else env
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", nargs="*", default=[])
    ap.add_argument("--entries", default=ENTRIES)
    ap.add_argument("--date", default=datetime.date.today().isoformat())
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    if not a.ids:
        print("no changed entries; nothing to check")
        return 0
    key = (env.get(KEY_ENV) or "").strip()
    if not key:
        print(
            "%s: %s is not set; no request made for %s"
            % (NEEDS_LABEL, KEY_ENV, " ".join(a.ids))
        )
        return 3
    by_id = {e["id"]: e for e in load_jsonl(a.entries)}
    missing = [i for i in a.ids if i not in by_id]
    if missing:
        print("unknown ids: %s" % " ".join(missing))
        return 1
    rows = []
    for i in a.ids:
        try:
            rows.append(check_entry(by_id[i], key, a.date, get))
        except (
            Exception
        ) as exc:  # network or parse failure is a reason to look, not a pass
            rows.append(
                dict(
                    {c: "" for c in COLUMNS},
                    problem_id=i,
                    verdict="UNCLEAR",
                    search_date=a.date,
                    notes="search failed: %s" % exc,
                )
            )
    out = a.out or "rows_%s.csv" % a.date
    with open(out, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)
    for r in rows:
        print("%s %s %s" % (r["problem_id"], r["verdict"], r["queries_run"]))
    print("wrote %s" % out)
    return 0 if all(r["verdict"] == "CURRENT" for r in rows) else 2


if __name__ == "__main__":
    sys.exit(main())
