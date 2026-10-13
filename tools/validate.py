"""Validate the registry.

  python tools/validate.py [--entries data/entries.jsonl] [--claims data/priority_claims.jsonl] [--root .]

Checks: every entry against schema.json; ids unique and EV-NNNNNN; aliases not shared by two
entries; claims link to existing ids; every certificate file exists and its sha256 matches;
every verifier_command runs on its certificate and prints the registered value (within the
entry's tolerance; exact certificates default to 1e-12); the provenance, fidelity and
feasibility rules in SCHEMA.md (see field_rules). Exit 0 when clean, 1 otherwise.
"""

import argparse
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ENTRIES, ROOT, SCHEMA, check, load_jsonl, num


def run_verifier(entry, root):
    c = entry["certificate"]
    argv = shlex.split(c["verifier_command"], posix=True)
    if argv and argv[0] == "python":
        argv[0] = sys.executable
    try:
        out = subprocess.run(
            argv, cwd=root, capture_output=True, text=True, timeout=600
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return "verifier did not run: %s" % exc
    if out.returncode != 0:
        return "verifier exit %d: %s" % (out.returncode, out.stderr.strip()[-300:])
    pat = c.get("value_pattern") or r"([-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)"
    m = re.search(pat, out.stdout)
    if not m:
        return "verifier output has no value matching %s" % pat
    got = float(m.group(1))
    tol = c.get("tolerance")
    if tol is None:
        tol = 1e-12 if c["verifier_kind"] == "exact" else 1e-9
    want = num(entry["current_value"])
    if want is None or abs(got - want) > tol:
        return "verifier printed %r, registered %r (tolerance %g)" % (
            got,
            entry["current_value"],
            tol,
        )
    return None


STATUS_VALUES = ("resolved", "open")


def field_rules(e):
    """Cross-field rules that schema.json cannot express."""
    errs = []
    if e.get("value_kind") == "status":
        if e.get("current_value") not in STATUS_VALUES:
            errs.append("status value must be one of %r" % (STATUS_VALUES,))
        if e.get("direction") != "unstated":
            errs.append("status value with direction %r" % e.get("direction"))
    elif e.get("current_value") in STATUS_VALUES:
        errs.append("status value %r without value_kind status" % e["current_value"])
    d = e.get("definition") or {}
    if d.get("status") == "curated" and e.get("fidelity") is None:
        errs.append("curated definition without a fidelity record")
    f = e.get("feasibility")
    if f:
        if f.get("definition_checked"):
            if not f.get("check_source"):
                errs.append("feasibility checked without check_source")
            if "result" not in f:
                errs.append("feasibility checked without result")
        elif f.get("result") not in (None, "not_checked"):
            errs.append("feasibility result %r without definition_checked" % f["result"])
        n = f.get("records_checked")
        if n is not None and f.get("records_infeasible", 0) + f.get("records_not_reproduced", 0) > n:
            errs.append("feasibility counts exceed records_checked")
    p = e.get("provenance") or {}
    for r in p.get("records", []):
        if r.get("date") and p.get("first_public_date") and r["date"] < p["first_public_date"]:
            errs.append("provenance record dated before first_public_date")
            break
    return errs


def validate(entries, claims, root, run=True):
    with open(SCHEMA, encoding="utf-8") as fh:
        schema = json.load(fh)
    errs, ids, alias_owner = [], set(), {}
    for e in entries:
        eid = e.get("id", "?")
        errs += ["%s %s" % (eid, x) for x in check(e, schema)]
        errs += ["%s %s" % (eid, x) for x in field_rules(e)]
        if eid in ids:
            errs.append("%s duplicate id" % eid)
        ids.add(eid)
        for a in e.get("aliases", []):
            key = (a.get("scheme"), a.get("id"), a.get("side"))
            if key in alias_owner and alias_owner[key] != eid:
                errs.append(
                    "%s alias %r already used by %s" % (eid, key, alias_owner[key])
                )
            alias_owner[key] = eid
        c = e.get("certificate") or {}
        if c.get("file"):
            path = os.path.join(root, c["file"])
            if not os.path.isfile(path):
                errs.append("%s certificate file missing: %s" % (eid, c["file"]))
                continue
            with open(path, "rb") as fh:
                digest = hashlib.sha256(fh.read()).hexdigest()
            if digest != c.get("sha256"):
                errs.append("%s sha256 mismatch for %s" % (eid, c["file"]))
            if not c.get("verifier_command"):
                errs.append("%s certificate without verifier_command" % eid)
            elif run:
                msg = run_verifier(e, root)
                if msg:
                    errs.append("%s %s" % (eid, msg))
        elif c.get("verifier_kind") != "external":
            errs.append(
                "%s non-external verifier_kind without a certificate file" % eid
            )
    for cl in claims:
        for ref in cl.get("entry_ids", []):
            if ref not in ids:
                errs.append(
                    "claim %s links unknown entry %s" % (cl.get("claim_id"), ref)
                )
    return errs


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--entries", default=ENTRIES)
    ap.add_argument(
        "--claims", default=os.path.join(ROOT, "data", "priority_claims.jsonl")
    )
    ap.add_argument(
        "--root", default=ROOT, help="directory certificate paths are relative to"
    )
    ap.add_argument("--no-run", action="store_true", help="skip running verifiers")
    a = ap.parse_args(argv)
    entries = load_jsonl(a.entries)
    claims = load_jsonl(a.claims) if os.path.isfile(a.claims) else []
    errs = validate(entries, claims, a.root, run=not a.no_run)
    certs = sum(1 for e in entries if e["certificate"].get("file"))
    for x in errs:
        print("ERROR", x)
    print(
        "%d entries, %d with certificates, %d claims: %s"
        % (
            len(entries),
            certs,
            len(claims),
            "OK" if not errs else "%d errors" % len(errs),
        )
    )
    return 0 if not errs else 1


if __name__ == "__main__":
    sys.exit(main())
