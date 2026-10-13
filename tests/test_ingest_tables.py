import os

import ingest_cohn
import ingest_packing_center
import validate
from conftest import ROOT, read

REAL = os.path.join(ROOT, "data", "entries.jsonl")

FRIEDMAN = """<TABLE><TR align=center><TD><font size=+3>1.<br><img src="t1.gif"><td>&nbsp;<TD><font size=+3>2.<br><img src="t2.gif"></tr>
<tr><td align=center><font size=+1>s = 2<br>Trivial.<TD><td align=center><font size=+1>s = 2 + 1/&radic;2 + &radic;6/2 = 3.931+<br>Found by Someone<br>in July 2008.</TR></TABLE>
<TABLE><TR><TD><font size=+3>3.<br><img src="t3.gif">
<br><font size=+1>s = 4.5+<br>Proved by Other<br>in 1964.<td>&nbsp;</TR></TABLE>"""

ELLSWORTH = """<!--
<div class="box"><font size="+3">1<br><a></a></font>
<div align="center"><font size="+1">$s = 9$<br>Commented out.</font></div></div>
-->
<div class="box"><font size="+3">2, 3<br><a><div class="svg-box"></div></a></font>
<div align="center"><font size="+1">$s = 2$<br>Proved by Someone<br>in early 1979.</font></div></div>
<div class="box"><font size="+3">5<br><a></a></font>
<div align="center"><font size="+1">$s = 2 + {1\\over 2}\\sqrt 2 = \\Nn{2.70710678118654}$<br>Found by Other in 1979.</font></div></div>"""

KISSING = """<table class="center" id="data"><thead><tr><th>Dimension</th><th>Lower bound</th></tr></thead><tbody>
<tr><td>4</td><td colspan="2">24</td><td>1</td><td>[<a title="Musin 2008" href="#21">21</a>]</td></tr>
<tr><td>5</td><td>40</td><td>44</td><td>1.100</td><td>[<a title="Korkine" href="#9">9</a>]</td></tr>
<tr><td>49</td><td>1</td><td>2</td><td>2</td><td></td></tr></tbody></table>"""

PACKING = """<table class="center" id="data"><thead><tr><th>n</th><th>Center density</th>
</thead><tbody>
<tr><td>12</td><td>3<sup>&minus;3</sup></td><td></td><td>0.0494541766242440&hellip;</td><td>0.0797117710668987</td><td>1.612</td><td></td></tr>
</tbody></table>"""


def test_packing_center_ingest():
    es = ingest_packing_center.build({"triinsqu": FRIEDMAN, "squinsqu": ELLSWORTH}, 1)
    by = {e["aliases"][0]["id"]: e for e in es}
    assert (
        by["triinsqu n=1"]["current_value"] == 2
        and by["triinsqu n=1"]["value_kind"] == "exact"
    )
    two = by["triinsqu n=2"]
    assert two["current_value"] == "3.931+" and two["value_kind"] == "record"
    assert two["provenance"]["first_public_date"] == "2008-07"
    assert (
        two["provenance"]["setter_kind"] == "unknown"
        and two["provenance"]["literature_status"] == "unknown"
    )
    assert by["triinsqu n=3"]["value_kind"] == "exact"  # stacked layout, "Proved"
    assert (
        by["squinsqu n=1"]["current_value"] == 1
        and by["squinsqu n=1"]["value_kind"] == "record"
    )  # unpictured: trivial packing
    assert (
        by["squinsqu n=3"]["current_value"] == 2
        and by["squinsqu n=3"]["value_kind"] == "exact"
    )
    assert by["squinsqu n=4"]["current_value"] == 2  # ceil(sqrt 4)
    assert by["squinsqu n=5"]["current_value"] == "2.70710678118654+"
    assert len([e for e in es if e["aliases"][0]["id"].startswith("squinsqu")]) == 50
    for e in es:
        assert validate.field_rules(e) == []
    rows = read(REAL)
    pc = [e for e in rows if e["aliases"][0]["scheme"] == "PackingCenter"]
    assert len(pc) == 144 and sum(e["value_kind"] == "exact" for e in pc) == 61
    tables = {e["aliases"][0]["id"].split()[0] for e in pc}
    assert tables == {"cirinsqu", "cirincir", "triinsqu", "squinsqu"}


def test_cohn_ingest_and_cross_links():
    existing = [
        {
            "id": "EV-000007",
            "aliases": [],
            "conflation_note": None,
            "variant_name": "k5 lower",
        },
        {
            "id": "EV-000228",
            "aliases": [],
            "conflation_note": None,
            "variant_name": "k5 upper",
        },
        {
            "id": "EV-000101",
            "aliases": [],
            "conflation_note": None,
            "variant_name": "lattice_packing_dim12",
        },
    ]
    new, touched = ingest_cohn.build(
        {"kissing-numbers": KISSING, "sphere-packing": PACKING}, 10, existing
    )
    ids = [e["aliases"][0]["id"] for e in new]
    assert ids == [
        "kissing-numbers d=4",
        "sphere-packing d=12",
    ]  # d=5 linked, d=49 out of range
    assert new[0]["current_value"] == 24 and new[0]["value_kind"] == "exact"
    assert (
        new[1]["current_value"]
        == "0.0494541766242440 <= Delta_12 <= 0.0797117710668987"
    )
    assert "EV-000101" in new[1]["conflation_note"]
    assert {"scheme": "Cohn", "id": "kissing-numbers d=5", "side": "upper"} in existing[
        1
    ]["aliases"]
    assert "40 to 44" in existing[0]["conflation_note"]
    assert sorted(set(touched)) == ["EV-000007", "EV-000101", "EV-000228"]
    rows = read(REAL)
    cohn = [e for e in rows if e["aliases"][0]["scheme"] == "Cohn"]
    assert len(cohn) == 91 and sum(e["value_kind"] == "exact" for e in cohn) == 11
    linked = [
        e
        for e in rows
        if e["aliases"][0]["scheme"] != "Cohn"
        and any(a["scheme"] == "Cohn" for a in e["aliases"])
    ]
    assert sorted(e["id"] for e in linked) == [
        "EV-000006",
        "EV-000007",
        "EV-000108",
        "EV-000109",
        "EV-000124",
        "EV-000228",
    ]
    assert all(e["conflation_note"] for e in linked)
