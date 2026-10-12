import json

import snapshot


def tree(reg):
    (reg / "data").mkdir()
    (reg / "entries.jsonl").replace(reg / "data" / "entries.jsonl")
    (reg / "README.md").write_text("r", encoding="utf-8")
    return reg


def test_snapshot_is_reproducible(reg, tmp_path):
    root = tree(reg)
    a = ["--root", str(root), "--no-validate", "--date", "2026-10-12"]
    assert snapshot.main(a + ["--out", str(tmp_path / "s1")]) == 0
    assert snapshot.main(a + ["--out", str(tmp_path / "s2")]) == 0
    b1 = (tmp_path / "s1" / "registry-2026-10-12.tar.gz").read_bytes()
    assert b1 == (tmp_path / "s2" / "registry-2026-10-12.tar.gz").read_bytes()
    m = json.loads(
        (tmp_path / "s1" / "registry-2026-10-12.manifest.json").read_text(
            encoding="utf-8"
        )
    )
    assert m["entries"] == 2 and "data/entries.jsonl" in m["files"]
    assert snapshot.main(a + ["--out", str(tmp_path / "s1")]) == 2  # never overwrites


def test_keep_prunes_old(reg, tmp_path):
    root = tree(reg)
    for d in ("2026-10-05", "2026-10-12", "2026-10-19"):
        snapshot.main(
            [
                "--root",
                str(root),
                "--no-validate",
                "--date",
                d,
                "--out",
                str(tmp_path),
                "--keep",
                "2",
            ]
        )
    assert sorted(p.name for p in tmp_path.glob("*.tar.gz")) == [
        "registry-2026-10-12.tar.gz",
        "registry-2026-10-19.tar.gz",
    ]
