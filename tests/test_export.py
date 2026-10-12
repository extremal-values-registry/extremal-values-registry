import csv

import export
from conftest import read


def test_export_writes_csv_and_pages(reg, tmp_path):
    out = tmp_path / "dist"
    assert export.main(["--entries", str(reg / "entries.jsonl"), "--out", str(out)]) == 0
    with open(out / "entries.csv", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert [r["id"] for r in rows] == ["EV-000001", "EV-000002"]
    assert rows[1]["aliases"] == "OptimizationConstants:29|lower"
    index = (out / "index.html").read_text(encoding="utf-8")
    assert 'href="entries/EV-000001.html"' in index and "verifier passes" in index
    page = (out / "entries" / "EV-000001.html").read_text(encoding="utf-8")
    for needle in ("toy definition", "<b>2.0</b>", "certificates/toy/cert.json", "Supersession chain", "Toy source"):
        assert needle in page


def test_export_escapes_html(reg, tmp_path):
    rows = read(reg / "entries.jsonl")
    rows[0]["variant_name"] = "<script>x</script>"
    p = tmp_path / "e.jsonl"
    p.write_text("".join(__import__("json").dumps(r) + "\n" for r in rows), encoding="utf-8")
    export.main(["--entries", str(p), "--out", str(tmp_path / "d")])
    assert "<script>x" not in (tmp_path / "d" / "entries" / "EV-000001.html").read_text(encoding="utf-8")
