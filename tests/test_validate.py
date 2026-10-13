import json
import os

import validate
from conftest import ROOT, read


def run(reg):
    return validate.main(["--entries", str(reg / "entries.jsonl"), "--claims", str(reg / "priority_claims.jsonl"),
                          "--root", str(reg)])


def test_fixture_registry_is_valid(reg):
    assert run(reg) == 0


def test_duplicate_id_rejected(reg):
    rows = read(reg / "entries.jsonl")
    rows[1]["id"] = rows[0]["id"]
    (reg / "entries.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    errs = validate.validate(rows, [], str(reg), run=False)
    assert any("duplicate id" in e for e in errs)


def test_schema_violation_rejected(reg):
    rows = read(reg / "entries.jsonl")
    rows[0]["direction"] = "sideways"
    del rows[1]["source"]
    errs = validate.validate(rows, [], str(reg), run=False)
    assert any("sideways" in e for e in errs) and any("missing source" in e for e in errs)


def test_sha_mismatch_rejected(reg):
    (reg / "certificates" / "toy" / "cert.json").write_text('{"values": [1, 2, 4]}', encoding="utf-8")
    errs = validate.validate(read(reg / "entries.jsonl"), [], str(reg))
    assert any("sha256 mismatch" in e for e in errs)


def test_verifier_value_mismatch_rejected(reg):
    rows = read(reg / "entries.jsonl")
    rows[0]["current_value"] = 1.9
    errs = validate.validate(rows, [], str(reg))
    assert any("verifier printed 2.0" in e for e in errs)


def test_claim_to_unknown_entry_rejected(reg):
    claims = read(reg / "priority_claims.jsonl")
    claims[0]["entry_ids"] = ["EV-999999"]
    errs = validate.validate(read(reg / "entries.jsonl"), claims, str(reg), run=False)
    assert any("unknown entry" in e for e in errs)


def test_shared_alias_rejected(reg):
    rows = read(reg / "entries.jsonl")
    rows[1]["aliases"].append(dict(scheme="HorizonMath", id="toy_mean"))
    errs = validate.validate(rows, [], str(reg), run=False)
    assert any("already used" in e for e in errs)


def test_real_registry_validates():
    assert validate.main([]) == 0


def test_real_certificate_value():
    rows = read(os.path.join(ROOT, "data", "entries.jsonl"))
    certified = [e for e in rows if e["certificate"]["file"]]
    assert len(certified) == 1
    e = certified[0]
    assert e["direction"] == "min" and e["current_value"] < 1.4688
    assert validate.run_verifier(e, ROOT) is None


def test_standard_version_absent_is_fine(reg):
    rows = read(reg / "entries.jsonl")
    assert all("standard_version" not in r for r in rows)
    assert validate.validate(rows, [], str(reg), run=False) == []


def test_standard_version_unknown_rejected(reg):
    rows = read(reg / "entries.jsonl")
    rows[0]["standard_version"] = "9.9"
    errs = validate.validate(rows, [], str(reg), run=False)
    assert any("9.9" in e for e in errs)


def test_standard_version_requirements(reg):
    rows = read(reg / "entries.jsonl")
    bad = dict(rows[0], standard_version="1.0", fidelity=None, status="unclear")
    bad["certificate"] = dict(bad["certificate"], file=None, verifier_kind="external")
    bad["provenance"] = dict(bad["provenance"], literature_status="unknown")
    errs = validate.standard_rules(bad)
    for want in ("fidelity", "exact certificate", "prior-art", "not current"):
        assert any(want in e for e in errs), want
    good = dict(rows[0], standard_version="1.0", status="current",
                fidelity={"statement_audit": "independent", "audit_note": "checked"})
    good["certificate"] = dict(good["certificate"], file="x", verifier_kind="exact", verifier_command="python v.py")
    good["provenance"] = dict(good["provenance"], literature_status="known_before")
    assert validate.standard_rules(good) == []
