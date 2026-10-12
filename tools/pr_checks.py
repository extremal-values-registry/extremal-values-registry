"""Checks run on a pull request (and by tools/dry_run_pr.py locally).

  python tools/pr_checks.py changed --base BASE_ENTRIES [--head data/entries.jsonl]
  python tools/pr_checks.py verify  --base BASE_ENTRIES [--head ...] [--root .]
  python tools/pr_checks.py identity --base BASE_ENTRIES [--head ...]

changed   prints the ids of entries that are new or differ from the base, one per line.
verify    re-runs every changed entry's verifier_command on its certificate in a fresh copy
          of the certificate directory (isolated python, no repository on sys.path) and checks
          the sha256 and the printed value. Exit 0 when all pass.
identity  enforces the identity rule: an existing id may not change its definition, domain,
          direction or units (that is a new variant, so a new id), ids are never removed, and a
          changed current_value must be strictly better and must move the old value into
          superseded[]. Exit 0 when clean.
"""

import argparse
import hashlib
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ENTRIES, ROOT, load_jsonl, num, strictly_better
from validate import run_verifier

IDENTITY_FIELDS = ("definition", "domain", "direction", "units_or_normalisation")


def changed_ids(base, head):
    old = {e["id"]: e for e in base}
    return [e["id"] for e in head if old.get(e["id"]) != e]


def identity_errors(base, head):
    errs = []
    old = {e["id"]: e for e in base}
    new = {e["id"]: e for e in head}
    for eid in old:
        if eid not in new:
            errs.append("%s removed: ids are permanent" % eid)
    for eid, e in new.items():
        o = old.get(eid)
        if o is None:
            continue
        for f in IDENTITY_FIELDS:
            if e.get(f) != o.get(f):
                # Transcribing a source_label definition into a curated one is allowed;
                # everything else about identity is frozen.
                if f == "definition" and o["definition"]["status"] == "source_label":
                    continue
                errs.append(
                    "%s changes %s: the definition is the identity, propose a new entry "
                    "with a conflation note instead" % (eid, f)
                )
        if e.get("current_value") != o.get("current_value"):
            if not strictly_better(
                e["direction"], e["current_value"], o["current_value"]
            ):
                errs.append(
                    "%s value %r is not strictly better than %r in direction %s"
                    % (eid, e["current_value"], o["current_value"], e["direction"])
                )
            if not any(
                num(s.get("value")) == num(o["current_value"])
                for s in e.get("superseded", [])
            ):
                errs.append(
                    "%s old value %r not recorded in superseded[]"
                    % (eid, o["current_value"])
                )
    return errs


def verify_isolated(entry, root):
    """Copy the certificate directory (and the verifier, if elsewhere) into an empty temp
    tree and run the verifier there, so it cannot read anything else in the repository."""
    c = entry["certificate"]
    if not c.get("file"):
        return None if c.get("verifier_kind") == "external" else "no certificate file"
    with tempfile.TemporaryDirectory(prefix="evr-verify-") as tmp:
        for rel in {
            os.path.dirname(c["file"]),
            os.path.dirname(c.get("verifier_file") or c["file"]),
        }:
            src = os.path.join(root, rel)
            if not os.path.isdir(src):
                return "certificate directory missing: %s" % rel
            shutil.copytree(src, os.path.join(tmp, rel), dirs_exist_ok=True)
        with open(os.path.join(tmp, c["file"]), "rb") as fh:
            if hashlib.sha256(fh.read()).hexdigest() != c.get("sha256"):
                return "sha256 mismatch for %s" % c["file"]
        return run_verifier(entry, tmp)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["changed", "verify", "identity"])
    ap.add_argument("--base", required=True, help="entries.jsonl of the target branch")
    ap.add_argument("--head", default=ENTRIES)
    ap.add_argument("--root", default=ROOT)
    a = ap.parse_args(argv)
    base = load_jsonl(a.base) if os.path.isfile(a.base) else []
    head = load_jsonl(a.head)
    ids = changed_ids(base, head)
    if a.cmd == "changed":
        print("\n".join(ids))
        return 0
    if a.cmd == "identity":
        errs = identity_errors(base, head)
        for x in errs:
            print("ERROR", x)
        print("identity rule: %s" % ("OK" if not errs else "%d errors" % len(errs)))
        return 0 if not errs else 1
    bad = 0
    by_id = {e["id"]: e for e in head}
    for eid in ids:
        e = by_id[eid]
        msg = verify_isolated(e, a.root)
        if e["certificate"].get("verifier_kind") == "external" and not e[
            "certificate"
        ].get("file"):
            print("%s external (no certificate; rests on the cited source)" % eid)
        elif msg:
            bad += 1
            print("%s FAIL %s" % (eid, msg))
        else:
            print("%s PASS verifier reproduces %r" % (eid, e["current_value"]))
    print(
        "verifiers: %d changed, %s" % (len(ids), "OK" if not bad else "%d failed" % bad)
    )
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
