"""Prepare a pull request that adds an entry or supersedes a value, without the maintainer.

  python tools/propose.py --definition def.json --value 1.46307... \
      --certificate path/to/construction.json --verifier path/to/verify.py \
      --citation "..." --url https://... --source-date YYYY-MM-DD --quote "verbatim quote" \
      [--verifier-kind exact|numeric] [--value-pattern REGEX] [--tolerance T] [--refereed] \
      [--entry EV-NNNNNN] [--slug name] [--date YYYY-MM-DD] [--out proposals/] [--root .]

def.json holds the identity of the variant: problem_family, variant_name, definition
{text, latex, status}, domain, direction, units_or_normalisation, and optionally aliases and
conflation_note. The definition is the identity: when (definition.text, domain, direction,
units_or_normalisation) equals an existing entry's, the proposal is a supersession of that
entry; otherwise it is a new entry with the next free id. --entry asserts which entry you
mean and fails if the definition does not match it.

Steps: copy the registry to a scratch tree, place the certificate and verifier under
certificates/<slug>/, write the entry, run the verifier in isolation on the certificate,
check the identity rule and strict improvement, run tools/validate.py on the whole scratch
tree. Only when every check passes does it write, under --out/<branch>/:
  entry.json      the entry as it will appear in data/entries.jsonl
  proposal.patch  unified diff against the current tree (git apply -p1 proposal.patch)
  files/          the changed files in repository layout
  PR_BODY.md      pull-request text with the check output and the commands to open it
It never touches the working tree, never commits and never pushes.
Exit 0 = proposal written, 1 = a check failed (nothing written), 2 = input error.
"""

import argparse
import copy
import datetime
import difflib
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ROOT, dump_jsonl, load_jsonl, strictly_better
from pr_checks import identity_errors, verify_isolated
from validate import validate

IDENTITY_KEYS = (
    "problem_family",
    "variant_name",
    "definition",
    "domain",
    "direction",
    "units_or_normalisation",
)
COPY = ("schema.json", "data", "certificates", "tools")


def norm(s):
    return " ".join(str(s or "").split()).lower()


def identity_key(e):
    return (
        norm(e["definition"]["text"]),
        norm(e["domain"]),
        e["direction"],
        norm(e["units_or_normalisation"]),
    )


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")[:60] or "entry"


def parse_value(s):
    try:
        v = float(s)
    except ValueError:
        return s
    return int(v) if re.fullmatch(r"[-+]?\d+", s.strip()) else v


def next_id(entries):
    return "EV-%06d" % (max([int(e["id"][3:]) for e in entries] or [0]) + 1)


def build_entry(a, ident, entries, cert_rel, verifier_rel, sha):
    match = [e for e in entries if identity_key(e) == identity_key(ident)]
    if a.entry and (not match or match[0]["id"] != a.entry):
        raise ValueError(
            "--entry %s does not have this definition (identity is definition.text, domain, direction, "
            "units); a different definition is a new entry" % a.entry
        )
    value = parse_value(a.value)
    cert = {
        "file": cert_rel,
        "verifier_file": verifier_rel,
        "sha256": sha,
        "verifier_command": "python -I %s %s" % (verifier_rel, cert_rel),
        "verifier_kind": a.verifier_kind,
        "verified_date": a.date,
        "value_pattern": a.value_pattern,
        "tolerance": a.tolerance,
    }
    source = {
        "citation": a.citation,
        "url": a.url,
        "date": a.source_date,
        "refereed": a.refereed,
    }
    note = "Quote: %s" % a.quote
    if match:
        old = match[0]
        if not strictly_better(old["direction"], value, old["current_value"]):
            raise ValueError(
                "%s: %r is not strictly better than %r (direction %s); equal is CURRENT"
                % (old["id"], value, old["current_value"], old["direction"])
            )
        e = copy.deepcopy(old)
        e["superseded"].append(
            {
                "value": old["current_value"],
                "source": old["source"]["citation"],
                "url": old["source"]["url"],
                "date": old["source"]["date"],
            }
        )
        e.update(
            current_value=value,
            certificate=cert,
            source=source,
            last_checked=a.date,
            status="current",
        )
        e["notes"] = (old["notes"] + " | " if old.get("notes") else "") + note
        return e, "supersede"
    e = {"id": next_id(entries)}
    for k in IDENTITY_KEYS:
        e[k] = ident[k]
    e.update(
        current_value=value,
        value_kind="bound",
        certificate=cert,
        source=source,
        superseded=[],
        aliases=ident.get("aliases", []),
        status="current",
        last_checked=a.date,
        conflation_note=ident.get("conflation_note"),
        notes=note,
    )
    return e, "new"


def text_diff(old, new, path):
    return "".join(
        difflib.unified_diff(
            old.splitlines(True),
            new.splitlines(True),
            "/dev/null" if old == "" else "a/" + path,
            "b/" + path,
        )
    )


def parser():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--definition", required=True)
    ap.add_argument("--value", required=True)
    ap.add_argument("--certificate", required=True)
    ap.add_argument("--verifier", required=True)
    ap.add_argument(
        "--verifier-kind",
        dest="verifier_kind",
        choices=["exact", "numeric"],
        default="exact",
    )
    ap.add_argument("--value-pattern", dest="value_pattern", default=None)
    ap.add_argument("--tolerance", type=float, default=None)
    ap.add_argument("--citation", required=True)
    ap.add_argument("--url", default=None)
    ap.add_argument("--source-date", dest="source_date", required=True)
    ap.add_argument(
        "--quote", required=True, help="verbatim quote of the value from the source"
    )
    ap.add_argument("--refereed", action="store_true")
    ap.add_argument("--entry", default=None, help="EV-NNNNNN you intend to supersede")
    ap.add_argument("--slug", default=None)
    ap.add_argument("--date", default=datetime.date.today().isoformat())
    ap.add_argument("--root", default=ROOT)
    ap.add_argument("--out", default="proposals")
    return ap


def main(argv=None):
    a = parser().parse_args(argv)
    try:
        with open(a.definition, encoding="utf-8") as fh:
            ident = json.load(fh)
        miss = [k for k in IDENTITY_KEYS if k not in ident]
        if miss:
            raise ValueError("definition file lacks: %s" % ", ".join(miss))
        if not a.quote.strip():
            raise ValueError("--quote must be a verbatim quote of the value")
        for p in (a.certificate, a.verifier):
            if not os.path.isfile(p):
                raise ValueError("no such file: %s" % p)
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", a.source_date):
            raise ValueError("--source-date must be YYYY-MM-DD")
        entries_path = os.path.join(a.root, "data", "entries.jsonl")
        base = load_jsonl(entries_path)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print("input error:", exc)
        return 2

    slug = a.slug or slugify(ident["variant_name"])
    cdir = "certificates/" + slug
    cert_rel = cdir + "/" + os.path.basename(a.certificate)
    verifier_rel = cdir + "/" + os.path.basename(a.verifier)
    with open(a.certificate, "rb") as fh:
        cert_bytes = fh.read()
    with open(a.verifier, "rb") as fh:
        ver_bytes = fh.read()
    sha = hashlib.sha256(cert_bytes).hexdigest()
    for rel, data in ((cert_rel, cert_bytes), (verifier_rel, ver_bytes)):
        existing = os.path.join(a.root, rel)
        if os.path.isfile(existing) and open(existing, "rb").read() != data:
            print(
                "input error: %s already exists with different content; pass --slug"
                % rel
            )
            return 2
    try:
        entry, kind = build_entry(a, ident, base, cert_rel, verifier_rel, sha)
    except ValueError as exc:
        print("check failed:", exc)
        return 1
    head = [entry if e["id"] == entry["id"] else e for e in base]
    if kind == "new":
        head.append(entry)

    log = []
    with tempfile.TemporaryDirectory(prefix="evr-propose-") as tmp:
        for name in COPY:
            src = os.path.join(a.root, name)
            if os.path.isdir(src):
                shutil.copytree(
                    src,
                    os.path.join(tmp, name),
                    ignore=shutil.ignore_patterns("__pycache__"),
                )
            elif os.path.isfile(src):
                shutil.copy2(src, os.path.join(tmp, name))
        os.makedirs(os.path.join(tmp, cdir), exist_ok=True)
        for rel, data in ((cert_rel, cert_bytes), (verifier_rel, ver_bytes)):
            with open(os.path.join(tmp, rel), "wb") as fh:
                fh.write(data)
        with open(
            os.path.join(tmp, "data", "entries.jsonl"),
            "w",
            encoding="utf-8",
            newline="\n",
        ) as fh:
            fh.write(dump_jsonl(head))
        msg = verify_isolated(entry, tmp)
        log.append(
            "verifier (isolated): %s"
            % (msg or "PASS, prints %r" % entry["current_value"])
        )
        ierrs = identity_errors(base, head)
        log.append("identity rule: %s" % ("OK" if not ierrs else "; ".join(ierrs)))
        claims_p = os.path.join(tmp, "data", "priority_claims.jsonl")
        verrs = validate(
            head,
            load_jsonl(claims_p) if os.path.isfile(claims_p) else [],
            tmp,
            run=False,
        )
        verrs += [x for x in [verify_isolated(entry, tmp)] if x]
        log.append("validate: %s" % ("OK" if not verrs else "; ".join(verrs[:5])))
    for line in log:
        print(line)
    if msg or ierrs or verrs:
        print("proposal NOT written: fix the failures above")
        return 1

    branch = "propose/%s-%s" % (entry["id"], a.date)
    out = os.path.join(a.out, branch.replace("/", "_"))
    files = os.path.join(out, "files")
    os.makedirs(os.path.join(files, cdir), exist_ok=True)
    os.makedirs(os.path.join(files, "data"), exist_ok=True)
    with open(os.path.join(a.root, "data", "entries.jsonl"), encoding="utf-8") as fh:
        old_text = fh.read()
    new_text = dump_jsonl(head)
    patch = text_diff(old_text, new_text, "data/entries.jsonl")
    for rel, data in ((cert_rel, cert_bytes), (verifier_rel, ver_bytes)):
        with open(os.path.join(files, rel), "wb") as fh:
            fh.write(data)
        p = os.path.join(a.root, rel)
        prev = open(p, encoding="utf-8").read() if os.path.isfile(p) else ""
        cur = data.decode("utf-8")
        if prev != cur:
            patch += text_diff(prev, cur, rel)
    with open(
        os.path.join(files, "data", "entries.jsonl"),
        "w",
        encoding="utf-8",
        newline="\n",
    ) as fh:
        fh.write(new_text)
    with open(os.path.join(out, "entry.json"), "w", encoding="utf-8") as fh:
        json.dump(entry, fh, indent=2, ensure_ascii=False)
    with open(
        os.path.join(out, "proposal.patch"), "w", encoding="utf-8", newline="\n"
    ) as fh:
        fh.write(patch)
    title = "%s %s: %s = %r" % (
        "Supersede" if kind == "supersede" else "Add",
        entry["id"],
        entry["variant_name"],
        entry["current_value"],
    )
    body = (
        [
            "# " + title,
            "",
            "Kind: %s. Branch: `%s`." % (kind, branch),
            "",
            'Source: %s (%s, %s). Quote: "%s"'
            % (a.citation, a.url or "no url", a.source_date, a.quote),
            "",
            "Checks run by tools/propose.py on %s:" % a.date,
            "",
        ]
        + ["- " + x for x in log]
        + [
            "",
            "To open the pull request from a clone of the registry:",
            "",
            "```",
            "git checkout -b %s" % branch,
            "git apply -p1 %s" % os.path.join(out, "proposal.patch").replace("\\", "/"),
            "python tools/validate.py && python -m pytest -q",
            "git add data/entries.jsonl %s" % cdir,
            'git commit -m "%s"' % title.replace('"', "'"),
            "git push -u origin %s   # then open the PR" % branch,
            "```",
            "",
            "Review: one approving review plus green `verify` checks (CONTRIBUTING.md).",
        ]
    )
    with open(os.path.join(out, "PR_BODY.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(body) + "\n")
    print("%s %s written to %s" % (kind, entry["id"], out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
