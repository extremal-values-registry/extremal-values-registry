"""Sample pull request, end to end, offline: the signed third-autocorrelation certificate.

  python examples/sample_pr/run.py

1. Copies the registry to a scratch tree and rolls EV-000004 back to its pre-certificate
   state (current value 1.4688 from the v2 paper, no certificate). That is the "base branch".
2. Runs tools/propose.py with EV-000004's definition, the value 1.4630715826075593, the
   certificate construction.json and its verify.py.
3. Applies the proposal's files to the scratch tree (what `git apply` does on the PR branch).
4. Runs tools/dry_run_pr.py, the local mirror of .github/workflows/verify.yml.
Writes propose.txt, summary.md and the proposal directory next to this script.
Exit 0 when the proposal is accepted and every check passes.
"""

import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
CERT = os.path.join(ROOT, "certificates", "third_autocorrelation_abs_inside")
sys.path.insert(0, os.path.join(ROOT, "tools"))
from common import dump_jsonl, load_jsonl


def scrub(path):
    """Replace local absolute paths with repository-relative ones in saved output."""
    if not os.path.isfile(path):
        return
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    for prefix in (ROOT, ROOT.replace("\\", "/")):
        text = text.replace(prefix + os.sep, "").replace(prefix + "/", "")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def main():
    entries = load_jsonl(os.path.join(ROOT, "data", "entries.jsonl"))
    cur = next(e for e in entries if e["id"] == "EV-000004")
    base_e = copy.deepcopy(cur)
    prev = base_e["superseded"].pop()  # 1.4688, arXiv 2511.02864
    base_e.update(
        current_value=prev["value"],
        source={
            "citation": "v2 paper, problem 6.4(a)",
            "url": prev["url"],
            "date": prev["date"],
            "refereed": False,
        },
        certificate={
            "file": None,
            "sha256": None,
            "verifier_command": None,
            "verifier_kind": "external",
            "verified_date": None,
            "value_pattern": None,
            "tolerance": None,
        },
        notes=None,
    )
    base = [base_e if e["id"] == "EV-000004" else e for e in entries]
    out_dir = os.path.join(HERE, "proposal")
    shutil.rmtree(out_dir, ignore_errors=True)
    with tempfile.TemporaryDirectory(prefix="evr-sample-pr-") as tmp:
        for name in (
            "schema.json",
            "pytest.ini",
            "data",
            "tools",
            "tests",
            "certificates",
        ):
            src = os.path.join(ROOT, name)
            dst = os.path.join(tmp, name)
            if os.path.isdir(src):
                shutil.copytree(
                    src,
                    dst,
                    ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"),
                )
            else:
                shutil.copy2(src, dst)
        shutil.rmtree(
            os.path.join(tmp, "certificates", "third_autocorrelation_abs_inside")
        )
        base_path = os.path.join(tmp, "base_entries.jsonl")
        for p in (base_path, os.path.join(tmp, "data", "entries.jsonl")):
            with open(p, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(dump_jsonl(base))
        ident = {
            k: cur[k]
            for k in (
                "problem_family",
                "variant_name",
                "definition",
                "domain",
                "direction",
                "units_or_normalisation",
            )
        }
        def_path = os.path.join(tmp, "def.json")
        with open(def_path, "w", encoding="utf-8") as fh:
            json.dump(ident, fh)
        p = subprocess.run(
            [
                sys.executable,
                "tools/propose.py",
                "--definition",
                def_path,
                "--value",
                repr(cur["current_value"]),
                "--certificate",
                os.path.join(CERT, "construction.json"),
                "--verifier",
                os.path.join(CERT, "verify.py"),
                "--value-pattern",
                cur["certificate"]["value_pattern"],
                "--tolerance",
                "1e-12",
                "--citation",
                cur["source"]["citation"],
                "--source-date",
                "2026-10-12",
                "--quote",
                "C(f) = 1.4630715826075593 (exact rational)",
                "--entry",
                "EV-000004",
                "--slug",
                "third_autocorrelation_abs_inside",
                "--date",
                "2026-10-12",
                "--out",
                out_dir,
            ],
            cwd=tmp,
            capture_output=True,
            text=True,
        )
        with open(os.path.join(HERE, "propose.txt"), "w", encoding="utf-8") as fh:
            fh.write(
                "$ python tools/propose.py ... --entry EV-000004\n"
                + p.stdout
                + p.stderr
                + "exit %d\n" % p.returncode
            )
        print(p.stdout + p.stderr)
        scrub(os.path.join(HERE, "propose.txt"))
        scrub(os.path.join(out_dir, "propose_EV-000004-2026-10-12", "PR_BODY.md"))
        if p.returncode:
            return p.returncode
        files = os.path.join(out_dir, "propose_EV-000004-2026-10-12", "files")
        shutil.copytree(files, tmp, dirs_exist_ok=True)
        d = subprocess.run(
            [
                sys.executable,
                "tools/dry_run_pr.py",
                "--base",
                base_path,
                "--root",
                tmp,
                "--summary",
                os.path.join(HERE, "summary.md"),
            ],
            cwd=tmp,
            capture_output=True,
            text=True,
            env={k: v for k, v in os.environ.items() if k != "LITERATURE_KEY"},
        )
        print(d.stdout[-3000:] + d.stderr)
        return d.returncode


if __name__ == "__main__":
    sys.exit(main())
