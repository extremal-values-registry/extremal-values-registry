import json

import badges
import export
from conftest import read


def _entry(i, status, checked, tables):
    return {
        "id": "EV-%06d" % i,
        "status": status,
        "last_checked": checked,
        "aliases": [{"scheme": "S", "id": str(i), "audit_table": t} for t in tables],
    }


ENTRIES = [
    _entry(1, "current", "2026-10-01", ["bench_a_audit"]),
    _entry(2, "unclear", "2026-10-05", ["bench_a_audit", "Bench B"]),
    _entry(3, "malformed", "2026-10-03", ["Bench B"]),
    _entry(4, "current", "2026-10-02", []),
]


def _load(p):
    return json.loads(p.read_text(encoding="utf-8"))


def test_entry_badges_schema_and_colors(tmp_path):
    assert badges.write_badges(ENTRIES, str(tmp_path)) == (4, 2)
    want = {1: ("current", "green"), 2: ("unclear", "yellow"), 3: ("malformed", "red")}
    for i, (status, color) in want.items():
        b = _load(tmp_path / "badge" / ("EV-%06d.json" % i))
        assert set(b) == {"schemaVersion", "label", "message", "color"}
        assert b["schemaVersion"] == 1 and b["label"] == "EV-%06d" % i
        assert b["color"] == color
        assert b["message"] == "%s · %s" % (status, ENTRIES[i - 1]["last_checked"])


def test_table_counts_and_registry(tmp_path):
    badges.write_badges(ENTRIES, str(tmp_path))
    a = _load(tmp_path / "badge" / "table" / "bench-a-audit.json")
    assert a["label"] == "bench_a_audit" and a["message"] == "1/2 current · 2026-10-05"
    b = _load(tmp_path / "badge" / "table" / "bench-b.json")
    assert b["message"] == "0/2 current · 2026-10-05" and b["color"] == "red"
    r = _load(tmp_path / "badge" / "registry.json")
    assert r == {"schemaVersion": 1, "label": "registry", "message": "4 entries · 2026-10-05", "color": "blue"}


def test_table_counts_each_entry_once(tmp_path):
    e = _entry(9, "current", "2026-10-01", ["t", "t"])
    badges.write_badges([e], str(tmp_path))
    assert _load(tmp_path / "badge" / "table" / "t.json")["message"] == "1/1 current · 2026-10-01"


def test_export_refreshes_badges(reg, tmp_path):
    out = tmp_path / "dist"
    export.main(["--entries", str(reg / "entries.jsonl"), "--out", str(out)])
    ids = [e["id"] for e in read(reg / "entries.jsonl")]
    for i in ids:
        assert _load(out / "badge" / (i + ".json"))["color"] == "green"
    assert _load(out / "badge" / "registry.json")["message"].startswith("%d entries · " % len(ids))
