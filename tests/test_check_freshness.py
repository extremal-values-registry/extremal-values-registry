import check_freshness
from conftest import read


def test_dry_run_proposes_but_never_writes(reg, capsys):
    before = (reg / "entries.jsonl").read_bytes()
    code = check_freshness.main([str(reg / "rows_2026-10-20.csv"), "--entries", str(reg / "entries.jsonl")])
    out = capsys.readouterr().out
    assert code == 2
    assert (reg / "entries.jsonl").read_bytes() == before
    assert "EV-000002: supersede 40 -> 41" in out
    assert "unmatched: HorizonMath no_such_problem" in out
    assert "EV-000001: STALE row not applied (needs primary/validator" in out
    assert out.count("\n+{") == 2 and "not written" in out


def test_apply_writes_supersession_and_last_checked(reg, capsys):
    code = check_freshness.main([str(reg / "rows_2026-10-20.csv"), "--entries", str(reg / "entries.jsonl"), "--apply"])
    assert code == 2
    a, b = read(reg / "entries.jsonl")
    assert a["current_value"] == 2.0 and a["last_checked"] == "2026-10-20"
    assert b["current_value"] == 41 and b["superseded"][-1]["value"] == 40
    assert b["source"]["url"] == "https://arxiv.org/abs/2610.00001" and b["last_checked"] == "2026-10-20"


def test_not_strictly_better_is_reported(reg, tmp_path, capsys):
    rows = tmp_path / "rows.csv"
    rows.write_text(",".join(check_freshness.COLUMNS) + "\n" +
                    "HorizonMath,toy_mean,2,v1,min,2026-09-01,s,STALE,2.0,arXiv:2601.00001,2026-08-01,primary,q,quote\n",
                    encoding="utf-8")
    assert check_freshness.main([str(rows), "--entries", str(reg / "entries.jsonl")]) == 0
    assert "not strictly better" in capsys.readouterr().out


def test_missing_columns_is_input_error(reg, tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("benchmark,problem_id\nx,y\n", encoding="utf-8")
    assert check_freshness.main([str(bad), "--entries", str(reg / "entries.jsonl")]) == 1
