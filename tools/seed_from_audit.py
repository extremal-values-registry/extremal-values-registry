"""Build the version-0 registry from the ancillary data of the stale-baselines audit.

Usage:
  python tools/seed_from_audit.py --src <dir holding the audit CSV tables> [--out data]

Every audited row becomes an entry or an alias of an existing entry. Rows that are the
same variant across tables are merged through the curated GROUPS map below. Stdlib only.
"""

import argparse
import csv
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CHECK_DATE = "2026-10-12"

TABLES = [
    ("alphaevolve_notebook_audit.csv", "AlphaEvolve-notebook"),
    ("alphaevolve_v2_paper_audit.csv", "AlphaEvolve-v2-paper"),
    ("horizonmath_baselines_audit.csv", "HorizonMath"),
    ("cross_benchmark_audit.csv", None),  # benchmark column decides the scheme
    ("einsteinarena_ranking.csv", "EinsteinArena"),
]
SCHEME = {
    "HorizonMath": "HorizonMath",
    "Optimization Constants in Mathematics": "OptimizationConstants",
    "EinsteinArena": "EinsteinArena",
}

# Leaderboard agent handles are not facts about the problem; they are redacted.
REDACT = [(re.compile(r"\bCodex\w*", re.IGNORECASE), "a leaderboard agent")]


def redact(s):
    for rx, rep in REDACT:
        s = rx.sub(rep, s)
    return s


# ---------------------------------------------------------------- curated variants
# key -> definition and the (scheme, problem_id) rows that are this exact variant.
GROUPS = {
    "ac1_upper": dict(
        family="Autocorrelation inequalities",
        name="First autocorrelation constant C1, upper bound",
        text="C1 = inf over nonnegative f supported on [-1/4,1/4] with positive integral of max_t (f*f)(t) / (int f)^2. Entries record the best upper bound (smallest ratio attained by an explicit f).",
        latex=r"C_1=\inf_{f\ge0,\ \operatorname{supp}f\subseteq[-\frac14,\frac14]}\frac{\max_t (f*f)(t)}{(\int f)^2}",
        domain="nonnegative functions on [-1/4,1/4]",
        direction="min",
        units="dimensionless ratio",
        rows=[
            ("AlphaEvolve-notebook", "B1_C1_upper"),
            ("AlphaEvolve-v2-paper", "6.2_C62_autoconv_upper"),
            ("HorizonMath", "autocorr_upper"),
            ("OptimizationConstants", "1a"),
            ("EinsteinArena", "First autocorrelation inequality"),
            ("EinsteinArena", "first-autocorrelation-inequality"),
        ],
    ),
    "ac2_lower": dict(
        family="Autocorrelation inequalities",
        name="Second autocorrelation constant C2, lower bound",
        text="C2 = sup over nonnegative f of ||f*f||_2^2 / (||f*f||_1 ||f*f||_inf). Entries record the best lower bound (largest ratio attained by an explicit f).",
        latex=r"C_2=\sup_{f\ge0}\frac{\|f*f\|_2^2}{\|f*f\|_1\,\|f*f\|_\infty}",
        domain="nonnegative functions on the real line",
        direction="max",
        units="dimensionless ratio",
        rows=[
            ("AlphaEvolve-notebook", "B2_C2_lower"),
            ("AlphaEvolve-v2-paper", "6.2_C63_autoconv_L2_lower"),
            ("EinsteinArena", "Second autocorrelation inequality"),
            ("EinsteinArena", "second-autocorrelation-inequality"),
        ],
    ),
    "ac3_validator": dict(
        family="Autocorrelation inequalities",
        name="Third autocorrelation constant, signed f, absolute value outside the maximum",
        text="For real (signed) f supported on [-1/4,1/4] with nonzero integral, the ratio |max_t (f*f)(t)| / (int f)^2, minimised over f; this is the quantity scored by the public benchmark validators. Entries record the best upper bound.",
        latex=r"C_3=\inf_{f:\ \operatorname{supp}f\subseteq[-\frac14,\frac14]}\frac{\left|\max_t (f*f)(t)\right|}{(\int f)^2}",
        domain="real-valued functions on [-1/4,1/4]",
        direction="min",
        units="dimensionless ratio",
        conflation="Often confused with the variant that takes the absolute value INSIDE the maximum, max_t |(f*f)(t)|. Example: the 2025 results notebook labels 1.4557 as C3 and 1.4688 as C3'; the later v2 paper labels the 1.4688 problem 6.4(a) (unprimed) and the 1.4557 problem 6.4'. Values from one variant do not bound the other. See the max-of-absolute-value entry.",
        rows=[
            ("AlphaEvolve-notebook", "B3_C3_upper"),
            ("AlphaEvolve-v2-paper", "6.2_C64prime_signed_upper"),
            ("HorizonMath", "autocorr_signed_upper"),
            ("EinsteinArena", "Third autocorrelation inequality"),
            ("EinsteinArena", "third-autocorrelation-inequality"),
        ],
    ),
    "ac3_abs_inside": dict(
        family="Autocorrelation inequalities",
        name="Third autocorrelation constant, signed f, maximum of the absolute value",
        text="C = the largest constant with max_t |(f*f)(t)| >= C (int f)^2 for every real f supported on [-1/4,1/4]. Any explicit f gives the upper bound C <= max_t |(f*f)(t)| / (int f)^2. Entries record the best upper bound.",
        latex=r"C=\inf_{f:\ \operatorname{supp}f\subseteq[-\frac14,\frac14],\ \int f\ne0}\frac{\max_t\left|(f*f)(t)\right|}{(\int f)^2}",
        domain="real-valued functions on [-1/4,1/4]",
        direction="min",
        units="dimensionless ratio",
        conflation="Not the same variant as the absolute-value-outside-the-maximum problem scored by benchmark validators (values near 1.449-1.4557). The 2025 notebook calls this one C3' (1.4688); the v2 paper calls it problem 6.4(a). Follow-on papers and leaderboards target the other variant.",
        rows=[
            ("AlphaEvolve-notebook", "B3_C3prime_upper"),
            ("AlphaEvolve-v2-paper", "6.2_C64_signed_upper"),
        ],
    ),
    "min_overlap": dict(
        family="Additive combinatorics",
        name="Erdős minimum overlap constant, upper bound",
        text="M = inf over measurable h:[0,2]->[0,1] with int h = 1 of max_k int h(x)(1 - h(x+k)) dx. Entries record the best upper bound.",
        latex=r"M=\inf_{h:[0,2]\to[0,1],\ \int h=1}\ \max_k\int h(x)\,(1-h(x+k))\,dx",
        domain="measurable h:[0,2]->[0,1]",
        direction="min",
        units="dimensionless",
        rows=[
            ("AlphaEvolve-notebook", "B5_C5_upper"),
            ("AlphaEvolve-v2-paper", "6.2_C65_min_overlap_upper"),
            ("EinsteinArena", "Erdos minimum overlap"),
            ("EinsteinArena", "erdos-min-overlap"),
            ("OptimizationConstants", "1b"),
        ],
    ),
    "kissing_11": dict(
        family="Sphere packing and kissing",
        name="Kissing number in dimension 11, lower bound",
        text="tau_11 = the maximum number of non-overlapping unit spheres in R^11 that touch a central unit sphere. Entries record the best lower bound (an explicit configuration).",
        latex=r"\tau_{11}\ \ge\ |X|,\quad X\subset S^{10},\ \langle x,y\rangle\le\tfrac12\ (x\ne y)",
        domain="point sets on the unit sphere S^10",
        direction="max",
        units="count",
        rows=[
            ("AlphaEvolve-notebook", "B11_kissing_d11"),
            ("AlphaEvolve-v2-paper", "6.4_kissing_n11_lower"),
            ("HorizonMath", "kissing_number_dim11"),
            ("EinsteinArena", "kissing-number-d11"),
            ("EinsteinArena", "kissing-number-d11-605"),
        ],
    ),
    "kissing_5": dict(
        family="Sphere packing and kissing",
        name="Kissing number in dimension 5, lower bound",
        text="tau_5 = the maximum number of non-overlapping unit spheres in R^5 touching a central unit sphere. Entries record the best lower bound.",
        latex=r"\tau_5",
        domain="point sets on S^4",
        direction="max",
        units="count",
        rows=[
            ("HorizonMath", "kissing_number_dim5"),
            ("OptimizationConstants", "29|lower"),
        ],
    ),
    "hex_11": dict(
        family="Packing",
        name="Packing 11 unit regular hexagons in a regular hexagon",
        text="Smallest side length of a regular hexagon that contains 11 non-overlapping regular hexagons of side 1.",
        latex=r"\min s:\ 11\ \text{unit hexagons}\subset H_s",
        domain="planar placements",
        direction="min",
        units="side length (unit hexagons)",
        rows=[
            ("AlphaEvolve-notebook", "B7_hex_n11"),
            ("AlphaEvolve-v2-paper", "6.19_hexagon_pack_n11"),
        ],
    ),
    "hex_12": dict(
        family="Packing",
        name="Packing 12 unit regular hexagons in a regular hexagon",
        text="Smallest side length of a regular hexagon that contains 12 non-overlapping regular hexagons of side 1.",
        latex=r"\min s:\ 12\ \text{unit hexagons}\subset H_s",
        domain="planar placements",
        direction="min",
        units="side length (unit hexagons)",
        rows=[
            ("AlphaEvolve-notebook", "B7_hex_n12"),
            ("AlphaEvolve-v2-paper", "6.19_hexagon_pack_n12"),
            ("EinsteinArena", "Hexagon packing (n=12)"),
        ],
    ),
    "maxmin_2d_16": dict(
        family="Point configurations",
        name="Max/min distance ratio, 16 points in the plane (squared)",
        text="Minimum over 16 points in R^2 of (max pairwise distance / min pairwise distance)^2.",
        latex=r"\min_{P\subset\mathbb R^2,|P|=16}\left(\frac{\max d}{\min d}\right)^2",
        domain="16-point sets in R^2",
        direction="min",
        units="squared ratio (some sources state the unsquared ratio)",
        conflation="Sources state either the ratio or its square: the v2 paper writes sqrt(12.889266112), the notebook and the arena write 12.889266112 / 12.88923. Compare squared values only.",
        rows=[
            ("AlphaEvolve-notebook", "B8_maxmin_2d_n16"),
            ("AlphaEvolve-v2-paper", "6.30_maxmin_d2_n16"),
            ("EinsteinArena", "min-distance-ratio-2d"),
            ("EinsteinArena", "Min distance ratio 2D (n=16)"),
        ],
    ),
    "maxmin_3d_14": dict(
        family="Point configurations",
        name="Max/min distance ratio, 14 points in R^3 (squared)",
        text="Minimum over 14 points in R^3 of (max pairwise distance / min pairwise distance)^2.",
        latex=r"\min_{P\subset\mathbb R^3,|P|=14}\left(\frac{\max d}{\min d}\right)^2",
        domain="14-point sets in R^3",
        direction="min",
        units="squared ratio",
        conflation="The v2 paper states sqrt(.) of the same squared values.",
        rows=[
            ("AlphaEvolve-notebook", "B8_maxmin_3d_n14"),
            ("AlphaEvolve-v2-paper", "6.30_maxmin_d3_n14"),
        ],
    ),
    "heil_tri_11": dict(
        family="Heilbronn problems",
        name="Heilbronn problem, 11 points in a unit-area equilateral triangle",
        text="Maximum over 11 points in an equilateral triangle of area 1 of the minimum area of a triangle formed by three of them.",
        latex=r"\max_{P}\min_{a,b,c\in P}\operatorname{area}(abc)",
        domain="11 points in a unit-area triangle",
        direction="max",
        units="area",
        rows=[
            ("AlphaEvolve-notebook", "B9_heiltri_n11"),
            ("AlphaEvolve-v2-paper", "6.29_heilbronn_eqtri_n11"),
        ],
    ),
    "heil_cvx_13": dict(
        family="Heilbronn problems",
        name="Heilbronn problem, 13 points in a convex region of unit area",
        text="Maximum over 13 points of min triangle area / area of their convex hull.",
        latex=r"\max_P\frac{\min_{a,b,c}\operatorname{area}(abc)}{\operatorname{area}(\operatorname{conv}P)}",
        domain="13 points in the plane",
        direction="max",
        units="area ratio",
        rows=[
            ("AlphaEvolve-notebook", "B10_heilconvex_n13"),
            ("AlphaEvolve-v2-paper", "6.29_heilbronn_convex_n13"),
        ],
    ),
    "heil_cvx_14": dict(
        family="Heilbronn problems",
        name="Heilbronn problem, 14 points in a convex region of unit area",
        text="Maximum over 14 points of min triangle area / area of their convex hull.",
        latex=r"\max_P\frac{\min_{a,b,c}\operatorname{area}(abc)}{\operatorname{area}(\operatorname{conv}P)}",
        domain="14 points in the plane",
        direction="max",
        units="area ratio",
        rows=[
            ("AlphaEvolve-notebook", "B10_heilconvex_n14"),
            ("AlphaEvolve-v2-paper", "6.29_heilbronn_convex_n14"),
            ("EinsteinArena", "Heilbronn convex (n=14)"),
        ],
    ),
    "circ_rect_21": dict(
        family="Packing",
        name="Sum of radii, 21 circles in a rectangle of perimeter 4",
        text="Maximum sum of radii of 21 disjoint circles inside a rectangle of perimeter 4.",
        latex=r"\max\sum_{i=1}^{21}r_i",
        domain="planar placements",
        direction="max",
        units="length",
        rows=[
            ("AlphaEvolve-notebook", "B13_cirRrec_n21"),
            ("EinsteinArena", "Circles in a rectangle (n=21)"),
            ("EinsteinArena", "circles-rectangle"),
        ],
    ),
    "ab_sumdiff": dict(
        family="Additive combinatorics",
        name="Sums and differences of two sets (|A+B| vs |A-B| exponent), lower bound",
        text="As stated in the AlphaEvolve materials (notebook B.6 / v2 paper 6.25 C_{6.44}). Entries record the best lower bound.",
        latex=r"C_{6.44}",
        domain="finite sets of integers",
        direction="max",
        units="exponent",
        rows=[
            ("AlphaEvolve-notebook", "B6_C6_lower"),
            ("AlphaEvolve-v2-paper", "6.25_C644_AplusB_lower"),
        ],
    ),
    "diff_bases": dict(
        family="Additive combinatorics",
        name="Difference bases constant, upper bound",
        text="lim k(n)^2 / n where k(n) is the minimum size of a difference basis for {1,...,n}. Entries record the best upper bound.",
        latex=r"\lim_{n\to\infty}\frac{k(n)^2}{n}",
        domain="finite sets of integers",
        direction="min",
        units="dimensionless",
        rows=[
            ("AlphaEvolve-v2-paper", "6.3_difference_bases_upper"),
            ("HorizonMath", "diff_basis_upper"),
        ],
    ),
    "ramsey_asym": dict(
        family="Ramsey theory",
        name="Diagonal Ramsey growth base, upper bound",
        text="Smallest c with R(k,k) <= (c+o(1))^k. Entries record the best upper bound.",
        latex=r"R(k,k)\le (c+o(1))^k",
        domain="graphs",
        direction="min",
        units="exponential base",
        rows=[("HorizonMath", "ramsey_asymptotic"), ("OptimizationConstants", "17")],
    ),
    "kakeya_01inf": dict(
        family="Additive combinatorics",
        name="Kakeya sums-differences constant (slopes 0,1,inf), lower bound",
        text="As defined in the Optimization Constants table entry 3b and v2 paper 6.15. Entries record the best lower bound.",
        latex=r"C_{3b}",
        domain="finite sets",
        direction="max",
        units="exponent",
        rows=[
            ("AlphaEvolve-v2-paper", "6.15_arith_kakeya_01inf"),
            ("OptimizationConstants", "3b|lower"),
        ],
    ),
    "kakeya_012inf": dict(
        family="Additive combinatorics",
        name="Kakeya sums-differences constant (slopes 0,1,2,inf), lower bound",
        text="As defined in the Optimization Constants table entry 3c and v2 paper 6.15. Entries record the best lower bound.",
        latex=r"C_{3c}",
        domain="finite sets",
        direction="max",
        units="exponent",
        rows=[
            ("AlphaEvolve-v2-paper", "6.15_arith_kakeya_012inf"),
            ("OptimizationConstants", "3c|lower"),
        ],
    ),
    "uncertainty_v2": dict(
        family="Harmonic analysis",
        name="Uncertainty inequality constant (v2 paper 6.6), upper bound",
        text="As stated in v2 paper problem 6.6 and notebook B.4 (second formulation). Entries record the best upper bound.",
        latex=r"C_{6.6}",
        domain="functions on R",
        direction="min",
        units="dimensionless",
        conflation="The arena 'uncertainty-principle' problem lists 0.31885, which is not comparable with 0.3102 as stated; it is a separate entry until a source shows the two are the same normalisation.",
        rows=[
            ("AlphaEvolve-notebook", "B4_C4_upper_f2"),
            ("AlphaEvolve-v2-paper", "6.6_uncertainty_upper"),
        ],
    ),
    "arena_uncertainty": dict(
        family="Harmonic analysis",
        name="Uncertainty principle problem (arena formulation)",
        text="As defined by the arena problem 'uncertainty-principle'.",
        latex="",
        domain="functions on R",
        direction="min",
        units="as defined by the arena",
        conflation="See the v2-paper uncertainty entry (0.3102); the two are listed separately.",
        rows=[
            ("EinsteinArena", "uncertainty-principle"),
            ("EinsteinArena", "Uncertainty inequality"),
        ],
    ),
    "arena_pnt": dict(
        family="Analytic number theory",
        name="Prime number theorem problem (arena formulation)",
        text="As defined by the arena problem 'prime-number-theorem'.",
        latex="",
        domain="as defined by the arena",
        direction="max",
        units="as defined by the arena",
        conflation="The v2 paper problem 6.12 lists 0.992619; the arena lists 0.994179 for its own formulation. Not merged.",
        rows=[
            ("EinsteinArena", "prime-number-theorem"),
            ("EinsteinArena", "Prime number theorem"),
        ],
    ),
    "arena_flat": dict(
        family="Polynomials",
        name="Flat polynomials, degree 69 (arena formulation)",
        text="As defined by the arena problem 'flat-polynomials'.",
        latex="",
        domain="degree-69 polynomials",
        direction="min",
        units="as defined by the arena",
        rows=[
            ("EinsteinArena", "flat-polynomials"),
            ("EinsteinArena", "Flat polynomials (deg 69)"),
        ],
    ),
    "arena_edges_tri": dict(
        family="Extremal graph theory",
        name="Edges versus triangles (arena formulation)",
        text="As defined by the arena problem 'edges-vs-triangles'.",
        latex="",
        domain="graphs",
        direction="max",
        units="as defined by the arena",
        rows=[
            ("EinsteinArena", "edges-vs-triangles"),
            ("EinsteinArena", "Edges vs triangles"),
        ],
    ),
    "arena_tammes_50": dict(
        family="Point configurations",
        name="Tammes problem, 50 points (arena formulation)",
        text="As defined by the arena; the audit notes the arena value 0.5633 is likely a different instance from the angular Tammes value 0.513472 (v2 paper 6.18).",
        latex="",
        domain="50 points on S^2",
        direction="max",
        units="as defined by the arena",
        rows=[("EinsteinArena", "Tammes (n=50)")],
    ),
}

FAMILY_HINTS = [
    (r"^rank_", "Matrix multiplication tensor rank"),
    (r"kissing", "Sphere packing and kissing"),
    (r"tammes|sph_design|spherical|no5sphere|design", "Point configurations"),
    (r"heil", "Heilbronn problems"),
    (r"kakeya|nikodym", "Kakeya-type problems"),
    (r"autocorr|autoconv", "Autocorrelation inequalities"),
    (r"pack|cir", "Packing"),
    (r"ramsey|schur|vdw|turan", "Ramsey theory"),
    (r"code|bklc|A21|covering|cwcode", "Coding theory"),
    (r"factorial", "Number theory"),
    (r"elliptic", "Arithmetic geometry"),
]


def direction_for(pid, pinned, better, notes, side=None):
    s = (pid + " " + (side or "")).lower()
    if side == "lower" or re.search(r"_lower\b|lower$", s):
        return "max"
    if side == "upper" or re.search(r"_upper\b|upper", s):
        return "min"
    m = re.search(r"Direction:\s*(minimi[sz]e|maximi[sz]e)", notes)
    if m:
        return "min" if m.group(1).startswith("minim") else "max"
    m = re.search(r"Side:\s*(lower|upper)", notes)
    if m:
        return "max" if m.group(1) == "lower" else "min"
    if pid.startswith("rank_") or re.search(
        r"sph_design|design_minimal|dts_|covering|crossing|keich", pid
    ):
        return "min"
    if re.search(
        r"tammes|no5sphere|isosceles|kissing|schur|lattice_packing|periodic_packing|vdw|cwcode|A21|bklc|"
        r"ramsey_coloring|elliptic|merit|heilbronn|cirR|beat_average|ring_loading|sofa|pnt|discrepancy",
        pid,
        re.IGNORECASE,
    ):
        return "max"
    a, b = num(pinned), num(better)
    if a is not None and b is not None and a != b:
        return "min" if b < a else "max"
    return "unstated"


NUM = re.compile(r"^\s*([-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)")


def num(s):
    if s is None:
        return None
    m = NUM.match(str(s))
    return float(m.group(1)) if m else None


def value_of(s):
    """Number if the string is a plain number (optionally followed by a parenthetical), else the trimmed string."""
    s = (s or "").strip()
    if not s:
        return None
    m = re.match(r"^\s*([-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)\s*(\(.*\))?\s*$", s)
    if m:
        x = m.group(1)
        return int(x) if re.fullmatch(r"[-+]?\d+", x) else float(x)
    return s


def url_of(source):
    m = re.search(r"https?://\S+", source or "")
    if m:
        return m.group(0).rstrip(";,)")
    m = re.search(r"arXiv:?\s*(\d{4}\.\d{4,5})", source or "", re.IGNORECASE)
    if m:
        return "https://arxiv.org/abs/" + m.group(1)
    return None


def date_of(s):
    m = re.search(r"\d{4}-\d{2}(?:-\d{2})?|\b(19|20)\d{2}\b", s or "")
    return m.group(0) if m else None


def decimals(raw):
    m = NUM.match(str(raw))
    if not m or "." not in m.group(1):
        return 0
    return len(m.group(1).split(".")[1].split("e")[0].split("E")[0])


def same(ra, rb):
    """Two stated values are the same if they agree at the shorter stated precision."""
    a, b = num(ra), num(rb)
    if a is None or b is None:
        return False
    d = min(decimals(ra), decimals(rb))
    return abs(a - b) <= 0.5 * 10 ** (-d) + 1e-15


def better(direction, ra, rb):
    a, b = num(ra), num(rb)
    if a is None or b is None or same(ra, rb):
        return False
    return a < b if direction == "min" else a > b if direction == "max" else False


def load_rows(src):
    rows = []
    for fname, scheme in TABLES:
        with open(os.path.join(src, fname), encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                r = {k: redact(v or "") for k, v in r.items()}
                if fname.startswith("einsteinarena_ranking"):
                    if r["section"] != "problem":
                        continue  # agent rows describe participants, not problems
                    rows.append(
                        dict(
                            table=fname,
                            scheme="EinsteinArena",
                            pid=r["problem"],
                            arena_num=r["problem_id"],
                            pinned=r["listed_value"],
                            verdict=r["verdict"],
                            better=r["audited_value"]
                            if r["verdict"] == "STALE"
                            else "",
                            source=r["audited_source"]
                            if r["verdict"] == "STALE"
                            else r["listed_source"],
                            source_date="",
                            notes="listed: " + r["listed_source"],
                            direction_hint=r["direction"],
                        )
                    )
                    continue
                sch = scheme or SCHEME[r["benchmark"]]
                rows.append(
                    dict(
                        table=fname,
                        scheme=sch,
                        pid=r["problem_id"],
                        pinned=r["pinned_value"],
                        verdict=r["verdict"],
                        better=r["better_value"],
                        source=r["source"],
                        source_date=r["source_date"],
                        notes=r["notes"],
                    )
                )
    return rows


def split_two_sided(row):
    """Optimization Constants rows 'lower: a; upper: b' are two variants (two directions)."""
    p = row["pinned"]
    if row["scheme"] == "OptimizationConstants" and "lower:" in p and "upper:" in p:
        lo, up = p.split("upper:", 1)
        lo = lo.replace("lower:", "").strip().rstrip(";").strip()
        out = []
        for side, val in (("lower", lo), ("upper", up.strip())):
            r = dict(row, pinned=val, side=side, pid_key=row["pid"] + "|" + side)
            out.append(r)
        return out
    m = re.match(r"^\s*([^/]+?)\s+/\s+([^/]+?)\s*$", p)
    if row["scheme"] == "OptimizationConstants" and m:
        bl, bu = (
            (row["better"].split("/", 1) + [""])[:2]
            if "/" in row["better"]
            else (row["better"], "")
        )
        side_note = re.search(r"Side:\s*(lower|upper|both)", row["notes"])
        return (
            [
                dict(
                    row,
                    pinned=m.group(1),
                    better=bl.strip(),
                    side="lower",
                    pid_key=row["pid"] + "|lower",
                ),
                dict(
                    row,
                    pinned=m.group(2),
                    better=bu.strip(),
                    side="upper",
                    pid_key=row["pid"] + "|upper",
                ),
            ]
            if side_note and side_note.group(1) == "both" or "/" in row["better"]
            else [dict(row, pid_key=row["pid"])]
        )
    side = re.search(r"Side:\s*(lower|upper)", row["notes"])
    if row["scheme"] == "OptimizationConstants" and side:
        return [dict(row, side=side.group(1), pid_key=row["pid"] + "|" + side.group(1))]
    return [dict(row, pid_key=row["pid"])]


def build(src):
    raw = load_rows(src)
    rows = [x for r in raw for x in split_two_sided(r)]
    index = {}
    for key, g in GROUPS.items():
        for sch, pid in g["rows"]:
            index[(sch, pid)] = key
    buckets, order = {}, []
    for r in rows:
        k = index.get((r["scheme"], r["pid_key"])) or index.get((r["scheme"], r["pid"]))
        if k is None:
            k = "row:" + r["scheme"] + ":" + r["pid_key"]
        if k not in buckets:
            buckets[k] = []
            order.append(k)
        buckets[k].append(r)
    missing = [
        (s, p)
        for (s, p), k in index.items()
        if k in buckets
        and not any(
            r["scheme"] == s and p in (r["pid"], r["pid_key"]) for r in buckets[k]
        )
    ]
    unmatched = [
        (s, p) for (s, p) in index if not any(index[(s, p)] == k for k in buckets)
    ]
    if missing or unmatched:
        sys.exit("curated row not found in tables: %r" % (missing + unmatched))

    # curated groups first (in GROUPS order), then table order
    order = [k for k in GROUPS if k in buckets] + [k for k in order if k not in GROUPS]
    entries, merges = [], 0
    for i, k in enumerate(order, 1):
        rs = buckets[k]
        merges += len(rs) - 1
        g = GROUPS.get(k)
        first = rs[0]
        if g:
            direction = g["direction"]
        else:
            hint = first.get("direction_hint", "")
            direction = {"minimize": "min", "maximize": "max"}.get(
                hint
            ) or direction_for(
                first["pid"],
                first["pinned"],
                first["better"],
                first["notes"],
                first.get("side"),
            )
        # candidates for the current value
        best, superseded, verdicts = None, [], []
        for r in rs:
            verdicts.append(r["verdict"])
            pv = value_of(r["pinned"])
            if r["verdict"] in ("STALE",) and r["better"]:
                cand = dict(
                    value=value_of(r["better"]),
                    raw=r["better"],
                    source=r["source"],
                    date=r["source_date"],
                    notes=r["notes"],
                    validator="validator" in (r["better"] + r["notes"]).lower(),
                )
                if pv is not None:
                    superseded.append(
                        dict(
                            value=pv,
                            source="%s listed value (%s)" % (r["scheme"], r["pid"]),
                            url=None,
                            date=None,
                        )
                    )
            elif (
                r["verdict"] in ("CURRENT", "STALE-LEADERBOARD", "UNCLEAR", "MALFORMED")
                and pv is not None
            ):
                cand = dict(
                    value=pv,
                    raw=r["pinned"],
                    source=r["source"] or ("%s listed value" % r["scheme"]),
                    date=r["source_date"],
                    notes=r["notes"],
                    validator=False,
                )
            else:
                cand = None
            if cand is None:
                continue
            if best is None or better(direction, cand["raw"], best["raw"]):
                if best is not None and num(best["raw"]) is not None:
                    superseded.append(
                        dict(
                            value=best["value"],
                            source=best["source"] or None,
                            url=url_of(best["source"]),
                            date=date_of(best["date"]),
                        )
                    )
                best = cand
            elif same(cand["raw"], best["raw"]) and decimals(cand["raw"]) > decimals(best["raw"]):
                best = cand  # same value stated more precisely
            elif num(cand["raw"]) is not None and not same(cand["raw"], best["raw"]):
                superseded.append(
                    dict(
                        value=cand["value"],
                        source=cand["source"] or None,
                        url=url_of(cand["source"]),
                        date=date_of(cand["date"]),
                    )
                )
        # dedupe superseded values, drop the current value, order worst -> best
        seen, chain = set(), []
        cur_num = num(best["raw"]) if best else None
        for s in superseded:
            sv = (
                num(s["value"])
                if not isinstance(s["value"], (int, float))
                else s["value"]
            )
            keyv = sv if sv is not None else s["value"]
            if keyv in seen or (sv is not None and best is not None and same(s["value"], best["raw"])):
                continue
            seen.add(keyv)
            chain.append(s)
        if direction in ("min", "max"):
            chain.sort(
                key=lambda s: (
                    (
                        num(s["value"])
                        if not isinstance(s["value"], (int, float))
                        else s["value"]
                    )
                    or 0
                ),
                reverse=(direction == "min"),
            )
        if "MALFORMED" in verdicts and not any(
            v in ("STALE", "CURRENT") for v in verdicts
        ):
            status = "malformed"
        elif best is None or ("UNCLEAR" in verdicts and "STALE" not in verdicts):
            status = "unclear"
        else:
            status = "current"
        aliases = []
        for r in rs:
            a = dict(scheme=r["scheme"], id=r["pid"])
            if r.get("side"):
                a["side"] = r["side"]
            if r.get("arena_num"):
                a["ranking_number"] = r["arena_num"]
            a["audit_table"] = r["table"].replace(".csv", "")
            a["audit_verdict"] = r["verdict"]
            aliases.append(a)
        if g:
            fam, name, text, latex, dom, units = (
                g["family"],
                g["name"],
                g["text"],
                g["latex"],
                g["domain"],
                g["units"],
            )
            def_status, conflation = "curated", g.get("conflation")
        else:
            fam = next(
                (f for rx, f in FAMILY_HINTS if re.search(rx, first["pid"], re.IGNORECASE)),
                "Uncategorised",
            )
            label = first["pid"]
            if first["scheme"] == "OptimizationConstants":
                label = (
                    "%s (constants-table %s)" % (first["notes"].strip(), first["pid"])
                    if first["verdict"] == "CURRENT"
                    else "Constants-table problem %s" % first["pid"]
                )
            name = label + (", %s bound" % first["side"] if first.get("side") else "")
            text = (
                "As stated in the source table row %s:%s. Exact functional not yet transcribed."
                % (first["scheme"], first["pid"])
            )
            latex, dom, units, def_status, conflation = (
                "",
                "as defined in the source",
                "as defined in the source",
                "source_label",
                None,
            )
        src = (best or {}).get("source", "") or ""
        notes_all = " | ".join(
            sorted(
                {
                    (r["table"].replace(".csv", "") + ": " + r["notes"][:600])
                    for r in rs
                    if r["notes"]
                }
            )
        )
        refereed = (
            bool(re.search(r"(?<!un)refereed", notes_all))
            and "unrefereed" not in notes_all
        )
        vkind = (
            "record"
            if (best and best["validator"])
            else (
                "exact"
                if status == "current"
                and direction in ("min", "max")
                and isinstance((best or {}).get("value"), (int, float))
                else "bound"
            )
        )
        if best and isinstance(best["value"], (int, float)) and status == "current":
            vkind = "record" if best["validator"] else "bound"
        entries.append(
            dict(
                id="EV-%06d" % i,
                problem_family=fam,
                variant_name=name,
                definition=dict(text=text, latex=latex, status=def_status),
                domain=dom,
                direction=direction,
                units_or_normalisation=units,
                current_value=(best or {}).get("value"),
                value_kind=vkind,
                certificate=dict(
                    file=None,
                    sha256=None,
                    verifier_command=None,
                    verifier_kind="external",
                    verified_date=None,
                    value_pattern=None,
                    tolerance=None,
                ),
                source=dict(
                    citation=src or None,
                    url=url_of(src),
                    date=date_of((best or {}).get("date", "")) if best else None,
                    refereed=refereed,
                ),
                superseded=chain,
                aliases=aliases,
                status=status,
                last_checked=CHECK_DATE,
                conflation_note=conflation,
                notes=notes_all or None,
            )
        )
    attach_certificate(entries)
    return entries, merges, len(rows), raw


def attach_certificate(entries):
    """The max-of-absolute-value third autocorrelation entry carries an exact certificate."""
    e = next(
        x
        for x in entries
        if x["variant_name"].startswith(
            "Third autocorrelation constant, signed f, maximum"
        )
    )
    d = "certificates/third_autocorrelation_abs_inside"
    cf, vf = d + "/construction.json", d + "/verify.py"
    with open(os.path.join(ROOT, cf), "rb") as fh:
        sha = hashlib.sha256(fh.read()).hexdigest()
    with open(os.path.join(ROOT, cf), encoding="utf-8") as fh:
        n = len(json.load(fh)["values"])
    old = dict(
        value=e["current_value"],
        source=e["source"]["citation"],
        url=e["source"]["url"],
        date=e["source"]["date"],
    )
    e["superseded"] = [s for s in e["superseded"] if s["value"] != 1.4993] + [old]
    e["superseded"].insert(
        0,
        dict(
            value=1.4993,
            source="prior bound cited by the v2 paper for problem 6.4(a)",
            url=None,
            date=None,
        ),
    )
    e["current_value"] = 1.4630715826075593
    e["value_kind"] = "bound"
    e["certificate"] = dict(
        file=cf,
        sha256=sha,
        verifier_command="python -I %s %s" % (vf, cf),
        verifier_kind="exact",
        verified_date=CHECK_DATE,
        value_pattern=r"C\(f\) = ([0-9.eE+-]+)",
        tolerance=1e-12,
        verifier_file=vf,
    )
    e["source"] = dict(
        citation="This registry, certificate certificates/third_autocorrelation_abs_inside "
        "(%d-cell step function; exact rational evaluation)" % n,
        url=None,
        date=CHECK_DATE,
        refereed=False,
    )
    e["status"] = "current"
    e["notes"] = (
        "Upper bound certified by exact rational arithmetic: max_t|f*f| over a step function is attained at a "
        "knot, so the ratio printed by the verifier is exact for the stored f. Not refereed. "
        + (e["notes"] or "")
    )


# ---------------------------------------------------------------- priority claims
CLAIM_RULES = [
    (
        r"first autocorrelation|1st autocorrelation|\bAC1\b|autoconvolution.*upper",
        "ac1_upper",
    ),
    (r"second autocorrelation|2nd autocorrelation|ACI ?2|\bAC2\b", "ac2_lower"),
    (r"third autocorrelation|3rd autocorrelation|\bAC3\b", "ac3"),
    (r"minimum overlap|min(imum)? overlap", "min_overlap"),
    (r"kissing.*(\b11\b|eleven)", "kissing_11"),
]


def link_claims(src, entries):
    key_to_id = {}
    for e in entries:
        for k, g in GROUPS.items():
            if e["variant_name"] == g["name"]:
                key_to_id[k] = e["id"]
    out = []
    with open(os.path.join(src, "novelty_claims_audit.csv"), encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            r = {k: redact(v or "") for k, v in r.items()}
            ids = []
            for rx, key in CLAIM_RULES:
                if re.search(rx, r["problem"], re.IGNORECASE):
                    if key == "ac3":
                        key = (
                            "ac3_abs_inside"
                            if "1.4688" in r["claimed_value"]
                            else "ac3_validator"
                        )
                    ids.append(key_to_id[key])
                    break
            out.append(
                dict(
                    claim_id=r["id"],
                    claimant=r["claimant"],
                    claim_date=r["claim_date"],
                    problem=r["problem"],
                    direction=r["direction"],
                    claimed_value=r["claimed_value"],
                    verdict=r["verdict"],
                    verdict_class=r["class"],
                    preexisting_value=r["preexisting_value"] or None,
                    preexisting_source=r["source"] or None,
                    preexisting_date=r["source_date"] or None,
                    lag_days=int(r["lag_days"])
                    if r["lag_days"].strip().lstrip("-").isdigit()
                    else None,
                    entry_ids=ids,
                    notes=r["notes"] or None,
                )
            )
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", default=os.path.join(ROOT, "data"))
    a = ap.parse_args()
    entries, merges, nrows, raw = build(a.src)
    claims = link_claims(a.src, entries)
    os.makedirs(a.out, exist_ok=True)
    with open(
        os.path.join(a.out, "entries.jsonl"), "w", encoding="utf-8", newline="\n"
    ) as fh:
        fh.writelines(json.dumps(e, ensure_ascii=False) + "\n" for e in entries)
    with open(
        os.path.join(a.out, "priority_claims.jsonl"),
        "w",
        encoding="utf-8",
        newline="\n",
    ) as fh:
        fh.writelines(json.dumps(c, ensure_ascii=False) + "\n" for c in claims)
    multi_table = sum(
        1 for e in entries if len({x["audit_table"] for x in e["aliases"]}) > 1
    )
    multi_scheme = sum(
        1 for e in entries if len({x["scheme"] for x in e["aliases"]}) > 1
    )
    print(
        "audited rows read: %d (after splitting two-sided rows: %d)" % (len(raw), nrows)
    )
    print("entries: %d" % len(entries))
    print("rows merged into an existing entry: %d" % merges)
    print(
        "entries spanning >1 audit table: %d; spanning >1 benchmark: %d"
        % (multi_table, multi_scheme)
    )
    print(
        "priority claims: %d (linked to an entry: %d)"
        % (len(claims), sum(1 for c in claims if c["entry_ids"]))
    )


if __name__ == "__main__":
    main()
