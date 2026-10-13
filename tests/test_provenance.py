import copy
import json
import os

import badges
import export
import ingest_erdos_wiki
import validate
from conftest import ROOT, read

REAL = os.path.join(ROOT, "data", "entries.jsonl")

WIKI = """
### 1(a). AI standalone

| Problem | AI systems | Date | Outcome |
| ------- | ---------- | ---- | ------- |
| [[7]](https://www.erdosproblems.com/7) | Model A | 3 Feb, 2026 | \U0001f7e1 Partial result
| [[7]](https://www.erdosproblems.com/7) | Model B | 9 Mar, 2026 | \U0001f7e2 Full solution (Lean)
| [[8]](https://www.erdosproblems.com/8) | Model A | 1 Jan, 2026 | \U0001f7e2 Solution to variant problem

### 1(b). AI alongside literature

| Problem | AI systems | Date | Outcome | Literature | Literature found on | Similar? |
| ------- | ---------- | ---- | ------- | ---------- | ------------------- | -------- |
| [[9]](https://www.erdosproblems.com/9) | Model C | 23 Mar-4 Apr, 2026 | \U0001f7e2 Full solution | \U0001f7e2 Someone (1990) | 5 Apr, 2026 | Yes

### 2(b). Formalization

| Problem | Proof to formalize | AI systems | Date |
| ------- | ------------------ | ---------- | -----|
| [[10]](https://www.erdosproblems.com/10) | \U0001f7e2 Someone (2012) | Prover | 23 Apr, 2026
"""


def by_alias(entries, scheme, ident):
    return [
        e
        for e in entries
        if any(a["scheme"] == scheme and a["id"] == ident for a in e["aliases"])
    ][0]


def test_wiki_parser_status_and_provenance():
    es = {
        e["aliases"][0]["id"]: e
        for e in ingest_erdos_wiki.build(WIKI, 1, "0" * 40, "2026-06-30")
    }
    assert sorted(es) == ["10", "7", "8", "9"]
    seven = es["7"]
    assert seven["current_value"] == "resolved" and seven["value_kind"] == "status"
    assert seven["provenance"]["setter_kind"] == "ai_system"
    assert seven["provenance"]["literature_status"] == "unknown"
    assert seven["provenance"]["first_public_date"] == "2026-02-03"
    assert seven["provenance"]["verification_state"] == "full"
    assert len(seven["provenance"]["records"]) == 2
    assert seven["fidelity"]["statement_audit"] == "none"  # Lean formalisation reported
    assert es["8"]["current_value"] == "open"  # green, but only for a variant
    assert es["9"]["provenance"]["literature_status"] == "found_after"
    assert es["9"]["provenance"]["first_public_date"] == "2026-03-23"
    assert es["10"]["current_value"] == "resolved"
    assert es["10"]["provenance"]["setter_kind"] == "human"
    assert es["10"]["provenance"]["literature_status"] == "known_before"
    assert seven["provenance"]["records"][0]["ai_systems"] == 1
    assert "Model" not in json.dumps(list(es.values()))
    for e in es.values():
        assert validate.field_rules(e) == []


def test_real_registry_new_sources():
    rows = read(REAL)
    erdos = [e for e in rows if e["aliases"][0]["scheme"] == "ErdosProblems"]
    ds1 = [e for e in rows if e["aliases"][0]["scheme"] == "DS1"]
    assert len(erdos) == 405 and len(ds1) == 72
    assert sum(e["value_kind"] == "exact" for e in ds1) == 9
    assert by_alias(rows, "DS1", "R(4,5)")["current_value"] == 25
    assert by_alias(rows, "DS1", "R(5,5)")["current_value"] == "43 <= R(5,5) <= 46"
    assert by_alias(rows, "DS1", "R(4,6)")["superseded"][0]["value"] == "R(4,6) <= 41"
    assert all(e["fidelity"]["statement_audit"] == "self" for e in ds1)
    assert {e["current_value"] for e in erdos} == {"resolved", "open"}


def test_every_entry_has_provenance_and_curated_has_fidelity():
    for e in read(REAL):
        assert e["provenance"]["setter_kind"] in (
            "human",
            "ai_system",
            "human_ai",
            "unknown",
        )
        if e["definition"]["status"] == "curated":
            assert e["fidelity"] is not None


def test_feasibility_cites_public_endpoint_only():
    rows = read(REAL)
    checked = [e for e in rows if (e["feasibility"] or {}).get("definition_checked")]
    assert len(checked) == 12
    for e in checked:
        assert e["feasibility"]["check_source"].startswith(
            "https://einsteinarena.com/api/solutions/best?problem_id="
        )
    assert (
        by_alias(rows, "EinsteinArena", "Tammes (n=50)")["feasibility"]["result"]
        == "infeasible"
    )
    for e in checked:
        f = e["feasibility"]
        assert ":\\" not in json.dumps(f) and ".jsonl" not in json.dumps(f)


def test_field_rules_reject_bad_combinations():
    e = copy.deepcopy(read(REAL)[0])
    e["value_kind"] = "status"
    assert any("status value" in x for x in validate.field_rules(e))
    e = copy.deepcopy(read(REAL)[0])
    e["fidelity"] = None
    assert any("fidelity" in x for x in validate.field_rules(e))
    e["feasibility"] = {
        "definition_checked": True,
        "check_source": None,
        "result": "feasible",
    }
    assert any("check_source" in x for x in validate.field_rules(e))
    e["feasibility"] = {
        "definition_checked": False,
        "check_source": None,
        "result": "infeasible",
    }
    assert any("without definition_checked" in x for x in validate.field_rules(e))


def test_schema_rejects_unknown_setter(reg):
    rows = read(reg / "entries.jsonl")
    rows[0]["provenance"]["setter_kind"] = "robot"
    errs = validate.validate(rows, [], str(reg), run=False)
    assert any("robot" in x for x in errs)


def test_export_and_badges_carry_new_fields(tmp_path):
    rows = read(REAL)
    export.export(rows, str(tmp_path))
    head = open(tmp_path / "entries.csv", encoding="utf-8").readline()
    for col in ("setter_kind", "literature_status", "statement_audit", "feasibility"):
        assert col in head
    page = open(tmp_path / "entries" / "EV-000001.html", encoding="utf-8").read()
    assert "Definition-level feasibility" in page and "Provenance" in page
    src = json.load(
        open(
            tmp_path / "badge" / "source" / "ds1-small-ramsey-numbers.json",
            encoding="utf-8",
        )
    )
    assert src["message"].startswith("72 entries")
    assert (
        badges.entry_badge(by_alias(rows, "EinsteinArena", "Tammes (n=50)"))["color"]
        == "red"
    )
