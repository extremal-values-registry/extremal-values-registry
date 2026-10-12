"""Weekly snapshot of the registry: a reproducible archive plus a manifest.

  python tools/snapshot.py [--out snapshots] [--date YYYY-MM-DD] [--keep 0] [--no-validate]

Runs tools/validate.py first (verifiers included) and refuses to snapshot a failing tree.
Writes snapshots/registry-<date>.tar.gz (sorted members, zeroed mtimes and owners, so the
same tree gives the same bytes) and snapshots/registry-<date>.manifest.json (sha256 of every
file and of the archive, entry and certificate counts, validate output). --keep N deletes all
but the newest N archives (0 keeps everything). Run weekly by .github/workflows/snapshot.yml;
upload the archive to the mirrors listed in DURABILITY.md.
Exit 0 = written, 1 = validate failed, 2 = snapshot for that date already exists.
"""

import argparse
import datetime
import glob
import gzip
import hashlib
import io
import json
import os
import subprocess
import sys
import tarfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ROOT, load_jsonl

INCLUDE = (
    "README.md",
    "SCHEMA.md",
    "CONTRIBUTING.md",
    "DURABILITY.md",
    "SUCCESSION.md",
    "LICENSE-CODE",
    "LICENSE-DATA",
    "schema.json",
    "pytest.ini",
    "data",
    "certificates",
    "tools",
    "tests",
    ".github",
)


def files_of(root):
    out = []
    for name in INCLUDE:
        p = os.path.join(root, name)
        if os.path.isfile(p):
            out.append(name)
        for d, dirs, fs in os.walk(p):
            dirs[:] = sorted(
                x for x in dirs if x not in ("__pycache__", ".pytest_cache")
            )
            out += [
                os.path.relpath(os.path.join(d, f), root).replace(os.sep, "/")
                for f in fs
                if not f.endswith(".pyc")
            ]
    return sorted(set(out))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def build_archive(root, names):
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w", format=tarfile.PAX_FORMAT) as tar:
        for n in names:
            with open(os.path.join(root, n), "rb") as fh:
                data = fh.read()
            ti = tarfile.TarInfo("registry/" + n)
            ti.size, ti.mtime, ti.mode, ti.uid, ti.gid, ti.uname, ti.gname = (
                len(data),
                0,
                0o644,
                0,
                0,
                "",
                "",
            )
            tar.addfile(ti, io.BytesIO(data))
    gz = io.BytesIO()
    with gzip.GzipFile(fileobj=gz, mode="wb", mtime=0, filename="") as g:
        g.write(raw.getvalue())
    return gz.getvalue()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=ROOT)
    ap.add_argument("--out", default=None)
    ap.add_argument("--date", default=datetime.date.today().isoformat())
    ap.add_argument("--keep", type=int, default=0)
    ap.add_argument("--no-validate", action="store_true")
    a = ap.parse_args(argv)
    out = a.out or os.path.join(a.root, "snapshots")
    archive = os.path.join(out, "registry-%s.tar.gz" % a.date)
    if os.path.exists(archive):
        print("snapshot exists: %s" % archive)
        return 2
    vout = "skipped"
    if not a.no_validate:
        p = subprocess.run(
            [
                sys.executable,
                os.path.join(a.root, "tools", "validate.py"),
                "--root",
                a.root,
                "--entries",
                os.path.join(a.root, "data", "entries.jsonl"),
                "--claims",
                os.path.join(a.root, "data", "priority_claims.jsonl"),
            ],
            capture_output=True,
            text=True,
        )
        vout = (
            p.stdout.strip().splitlines()[-1] if p.stdout.strip() else p.stderr.strip()
        )
        if p.returncode:
            print("validate failed, no snapshot:\n" + p.stdout + p.stderr)
            return 1
    names = files_of(a.root)
    data = build_archive(a.root, names)
    os.makedirs(out, exist_ok=True)
    with open(archive, "wb") as fh:
        fh.write(data)
    entries = load_jsonl(os.path.join(a.root, "data", "entries.jsonl"))
    manifest = {
        "date": a.date,
        "archive": os.path.basename(archive),
        "archive_sha256": sha(data),
        "entries": len(entries),
        "certificates": sum(1 for e in entries if e["certificate"].get("file")),
        "validate": vout,
        "files": {n: sha(open(os.path.join(a.root, n), "rb").read()) for n in names},
    }
    with open(
        archive.replace(".tar.gz", ".manifest.json"), "w", encoding="utf-8"
    ) as fh:
        json.dump(manifest, fh, indent=1, sort_keys=True)
    if a.keep > 0:
        for old in sorted(glob.glob(os.path.join(out, "registry-*.tar.gz")))[: -a.keep]:
            os.remove(old)
            m = old.replace(".tar.gz", ".manifest.json")
            if os.path.exists(m):
                os.remove(m)
    print(
        "wrote %s (%d files, sha256 %s)"
        % (archive, len(names), manifest["archive_sha256"])
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
