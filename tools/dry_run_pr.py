"""Run the steps of .github/workflows/verify.yml locally, in the same order.

  python tools/dry_run_pr.py --base BASE_ENTRIES [--root .] [--summary summary.md]

1. tools/validate.py on the head tree (schema, ids, aliases, sha256, every verifier)
2. tools/pr_checks.py identity (definition is identity; strict improvement; superseded[])
3. tools/pr_checks.py verify (changed entries' verifiers, isolated copy of each certificate)
4. tools/literature_check.py on changed ids (exit 3 without a key -> label, not a failure)
5. python -m pytest -q
Prints a check summary (and writes it to --summary). Exit 0 when steps 1-3 and 5 pass.
The workflow additionally runs step 3 inside a clean container with no network.
"""

import argparse
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def run(argv, cwd):
    p = subprocess.run([sys.executable] + argv, cwd=cwd, capture_output=True, text=True)
    return p.returncode, (p.stdout + p.stderr).strip()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--root", default=os.path.dirname(HERE))
    ap.add_argument("--summary", default=None)
    ap.add_argument("--skip-pytest", action="store_true")
    a = ap.parse_args(argv)
    root, base = os.path.abspath(a.root), os.path.abspath(a.base)
    head = os.path.join(root, "data", "entries.jsonl")
    steps, labels = [], []
    code, out = run(["tools/validate.py"], root)
    steps.append(("validate", code == 0, out))
    code, out = run(
        ["tools/pr_checks.py", "identity", "--base", base, "--head", head], root
    )
    steps.append(("identity rule", code == 0, out))
    code, out = run(
        [
            "tools/pr_checks.py",
            "verify",
            "--base",
            base,
            "--head",
            head,
            "--root",
            root,
        ],
        root,
    )
    steps.append(("changed verifiers", code == 0, out))
    _, ids = run(
        ["tools/pr_checks.py", "changed", "--base", base, "--head", head], root
    )
    ids = ids.split()
    code, out = run(
        ["tools/literature_check.py", "--entries", head, "--ids"] + ids, root
    )
    if code == 3:
        labels.append("needs-literature-check")
    steps.append(
        (
            "literature check (two passes)",
            True,
            out + ("" if code != 2 else "\n(candidates: reviewer reads them)"),
        )
    )
    if not a.skip_pytest:
        code, out = run(["-m", "pytest", "-q"], root)
        tail = [x for x in out.splitlines() if re.search(r"\d+ (passed|failed|error)", x)]
        steps.append(("pytest", code == 0, tail[-1] if tail else out[-500:]))
    ok = all(s[1] for s in steps)
    lines = [
        "## Registry checks: %s" % ("PASS" if ok else "FAIL"),
        "",
        "Changed entries: %s" % (", ".join(ids) or "none"),
        "",
    ]
    for name, passed, out in steps:
        lines += [
            "### %s: %s" % (name, "pass" if passed else "FAIL"),
            "```",
            out,
            "```",
            "",
        ]
    lines.append("Labels: %s" % (", ".join(labels) or "none"))
    text = "\n".join(lines) + "\n"
    print(text)
    if a.summary:
        with open(a.summary, "w", encoding="utf-8") as fh:
            fh.write(text)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
