import json

import literature_check
import pr_checks
import propose
from conftest import read

IDENT = dict(
    problem_family="Toy",
    variant_name="Toy mean",
    definition={"text": "toy definition", "latex": "x", "status": "curated"},
    domain="toy",
    direction="min",
    units_or_normalisation="none",
)
VERIFIER = 'import json,sys\nv=json.load(open(sys.argv[1]))["values"]\nprint("value =", sum(v)/len(v))\n'


def setup(reg, tmp_path, values, ident=IDENT):
    d = tmp_path / "in"
    d.mkdir(exist_ok=True)
    (d / "def.json").write_text(json.dumps(ident), encoding="utf-8")
    (d / "cert.json").write_text(json.dumps({"values": values}), encoding="utf-8")
    (d / "check.py").write_text(VERIFIER, encoding="utf-8")
    (reg / "data").mkdir()
    (reg / "entries.jsonl").replace(reg / "data" / "entries.jsonl")
    (reg / "priority_claims.jsonl").replace(reg / "data" / "priority_claims.jsonl")
    (reg / "schema.json").write_text(
        open(propose.ROOT + "/schema.json", encoding="utf-8").read(), encoding="utf-8"
    )
    return d


def args(reg, d, value, *extra):
    return [
        "--definition",
        str(d / "def.json"),
        "--value",
        value,
        "--certificate",
        str(d / "cert.json"),
        "--verifier",
        str(d / "check.py"),
        "--value-pattern",
        r"value = ([0-9.eE+-]+)",
        "--citation",
        "Toy paper",
        "--url",
        "https://example.org/p",
        "--source-date",
        "2026-10-11",
        "--quote",
        "mean 1.5",
        "--date",
        "2026-10-12",
        "--root",
        str(reg),
        "--out",
        str(reg / "out"),
        "--slug",
        "toy2",
    ] + list(extra)


def test_supersession_written_and_verified(reg, tmp_path, capsys):
    d = setup(reg, tmp_path, [1, 2])
    before = (reg / "data" / "entries.jsonl").read_bytes()
    assert propose.main(args(reg, d, "1.5", "--entry", "EV-000001")) == 0
    out = reg / "out" / "propose_EV-000001-2026-10-12"
    e = json.loads((out / "entry.json").read_text(encoding="utf-8"))
    assert e["id"] == "EV-000001" and e["current_value"] == 1.5
    assert (
        e["superseded"][-1]["value"] == 2.0
        and e["certificate"]["file"] == "certificates/toy2/cert.json"
    )
    patch = (out / "proposal.patch").read_text(encoding="utf-8")
    assert (
        "+++ b/data/entries.jsonl" in patch
        and "+++ b/certificates/toy2/cert.json" in patch
    )
    assert "git checkout -b propose/EV-000001-2026-10-12" in (
        out / "PR_BODY.md"
    ).read_text(encoding="utf-8")
    assert (
        reg / "data" / "entries.jsonl"
    ).read_bytes() == before  # working tree untouched
    head = read(out / "files" / "data" / "entries.jsonl")
    assert pr_checks.identity_errors(read(reg / "data" / "entries.jsonl"), head) == []


def test_not_strictly_better_rejected(reg, tmp_path, capsys):
    d = setup(reg, tmp_path, [2, 2])
    assert propose.main(args(reg, d, "2.0")) == 1
    assert "not strictly better" in capsys.readouterr().out
    assert not (reg / "out").exists()


def test_verifier_disagreement_writes_nothing(reg, tmp_path, capsys):
    d = setup(reg, tmp_path, [1, 2])
    assert propose.main(args(reg, d, "1.4")) == 1
    assert (
        "verifier printed 1.5" in capsys.readouterr().out and not (reg / "out").exists()
    )


def test_new_definition_gets_new_id(reg, tmp_path):
    d = setup(
        reg,
        tmp_path,
        [1, 2],
        dict(
            IDENT,
            definition={
                "text": "toy mean, other normalisation",
                "latex": "y",
                "status": "curated",
            },
        ),
    )
    assert propose.main(args(reg, d, "1.5")) == 0
    e = json.loads(
        (reg / "out" / "propose_EV-000003-2026-10-12" / "entry.json").read_text(
            encoding="utf-8"
        )
    )
    assert e["id"] == "EV-000003" and e["superseded"] == []


def test_entry_flag_must_match_definition(reg, tmp_path, capsys):
    d = setup(reg, tmp_path, [1, 2], dict(IDENT, direction="max"))
    assert propose.main(args(reg, d, "1.5", "--entry", "EV-000001")) == 1
    assert "does not have this definition" in capsys.readouterr().out


def test_missing_quote_is_input_error(reg, tmp_path):
    d = setup(reg, tmp_path, [1, 2])
    a = args(reg, d, "1.5")
    a[a.index("--quote") + 1] = " "
    assert propose.main(a) == 2


def test_identity_rule_blocks_definition_change(reg):
    base = read(reg / "entries.jsonl")
    head = json.loads(json.dumps(base))
    head[0]["domain"] = "other"
    del head[1]
    errs = pr_checks.identity_errors(base, head)
    assert any("changes domain" in x for x in errs) and any(
        "removed" in x for x in errs
    )


def test_literature_check_without_key_labels(reg, capsys):
    code = literature_check.main(
        ["--ids", "EV-000001", "--entries", str(reg / "entries.jsonl")], env={}
    )
    assert code == 3 and "needs-literature-check" in capsys.readouterr().out


def test_literature_check_two_passes_offline(reg, tmp_path):
    calls = []

    def fake_get(url):
        calls.append(url)
        if "openalex" in url:
            return json.dumps({"results": []})
        return (
            "<feed><entry><id>http://arxiv.org/abs/2610.1</id><title>Toy mean bound</title>"
            "<published>2026-10-01T00:00:00Z</published></entry></feed>"
        )

    out = tmp_path / "rows.csv"
    code = literature_check.main(
        [
            "--ids",
            "EV-000001",
            "--entries",
            str(reg / "entries.jsonl"),
            "--out",
            str(out),
            "--date",
            "2026-10-12",
        ],
        get=fake_get,
        env={"LITERATURE_KEY": "k"},
    )
    assert code == 2 and len(calls) == 2
    text = out.read_text(encoding="utf-8")
    assert "UNCLEAR" in text and "Toy mean bound" in text and "STALE" not in text
