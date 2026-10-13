# Extremal Values Registry

**A quarter of the "best known" values in AI-math benchmarks are already beaten. This registry tracks the real frontier.**

[![DOI](https://img.shields.io/badge/DOI-10.5281%2Fzenodo.23326558-blue)](https://doi.org/10.5281/zenodo.23326558)
![License: CC BY 4.0 + MIT](https://img.shields.io/badge/license-CC%20BY%204.0%20%2B%20MIT-green)
![entries: 1034](https://img.shields.io/badge/entries-1034-informational)
![verified certificates: 1](https://img.shields.io/badge/verified%20certificates-1-success)

One entry per problem **variant**: the exact definition, the current best value, the source,
the chain of values it superseded, and the names that benchmarks and leaderboards use for
it. Think of OEIS, but for best-known bounds. A benchmark can pin an entry id (`EV-000004`)
instead of copying a number that goes stale.

## 60-second tour

```
git clone https://github.com/extremal-values-registry/extremal-values-registry
cd extremal-values-registry
python tools/validate.py                       # 1034 entries, 1 with certificates, 231 claims: OK
cd certificates/third_autocorrelation_abs_inside
python -I verify.py construction.json          # exact check, under a second
```

One entry, as a card:

| | |
|---|---|
| **Id** | `EV-000004` |
| **Variant** | Third autocorrelation constant, signed f, maximum of the absolute value |
| **Definition** | C = the largest constant with max_t abs((f*f)(t)) >= C (int f)^2 for every real f supported on [-1/4, 1/4]. Any explicit f gives an upper bound; the entry records the best one. |
| **Direction** | min (dimensionless ratio) |
| **Current value** | **1.4630716** (upper bound), exact rational certificate, verified 2026-10-12 |
| **Source** | this registry, `certificates/third_autocorrelation_abs_inside` (300-cell step function) |
| **Superseded chain** | 1.4993 (prior bound) -> 1.4688 (arXiv 2511.02864, 2025-11-03) -> **1.4630716** |
| **Aliases** | `B3_C3prime_upper` (notebook table), `6.2_C64_signed_upper` (paper table) |
| **Conflation note** | Not the same variant as the one scored by benchmark validators (values near 1.449-1.4557). See below. |

Every entry is a line of `data/entries.jsonl`; `python tools/export.py --out dist` renders
a CSV and a static HTML page per entry.

## Why it exists

Our published audit (https://doi.org/10.5281/zenodo.23324073) checked five "best known"
tables used to evaluate and report AI-driven mathematics (HorizonMath, the Optimization
Constants in Mathematics table, EinsteinArena, and two AlphaEvolve result sets):

- **69 of 268 targets (25.7%)** are superseded or not scoreable as written.
- **48 of 231 AI-discovery improvement claims (20.8%)** had an equal-or-better value published
  before the claim; **17 (7.4%)** came from a third party the claimant did not cite.
- Correcting **five** stale values on one public arena leaderboard reorders its top 10
  (**7 reversals**), and **57%** of recorded "beats" sat on stale rows.
- **603 of 603** public records re-scored with their benchmarks' own validators were valid:
  the records are fine, the reference values are what rot. Checked against the problems'
  written definitions instead of the validators, some are not: see `feasibility` below.
- Classical OR libraries (TSPLIB, QAPLIB, CVRPLIB, MIPLIB, OR-Library) showed **0 stale rows
  of 158**. The decay is specific to young AI-era tables, which is why they need a registry.

This registry holds **1034 entries** (970 current, 50 unclear, 14 malformed) and **231 priority
claims** linked to entry ids: the 322 audited benchmark variants, 405 Erdős problems from the
AI-contributions wiki (frozen 2026-06-30) and the 72 cells of the classical two-colour Ramsey
table R(k,l), k <= l <= 15, from Radziszowski's survey DS1, 144 cells (n <= 50) of four tables
of Erich Friedman's Packing Center, and 91 new cells (plus 6 cross-linked) of Henry Cohn's kissing-number
and sphere-packing tables, dimensions 1-48. To audit your own table, use
the sibling [`freshcheck`](https://github.com/extremal-values-registry/freshcheck) repository (same owner; the registry accepts its row format via `tools/check_freshness.py`).

## What makes an entry a fact

**An entry is a fact only when its verifier passes. Until then it is a sourced claim.**
Today one entry carries an exact certificate: the signed third-autocorrelation constant,
upper bound 1.4688 -> 1.4630716, checked with `python -I verify.py construction.json`
(exact rational arithmetic, under a second). The other 1033 rest on a cited primary source
with a verbatim quote (`verifier_kind: external`). A superseding value must be strictly
better in the entry's direction, for the same variant.

## Provenance, fidelity, feasibility

Every entry also records **who set the value** (`provenance`: human, AI system, human with AI,
or unknown; whether comparable literature was unknown, found afterwards or known before, in the
taxonomy of the Erdős-problems AI-contributions wiki; first public date; where), **whether the
formal statement was audited** (`fidelity`: none, self, independent) and, for leaderboard-derived
values, **whether the records satisfy the written definition** (`feasibility`). For the twelve
EinsteinArena-derived entries every public record in the arena's bulk endpoint
(`https://einsteinarena.com/api/solutions/best?problem_id=N`) was re-checked against the
problem's definition, independently of the platform's scorer; the detailed results are under
review with the platform maintainers and will be published when that review concludes. See `SCHEMA.md`.

## Known conflations

Benchmarks routinely give two different problems the same name. Example: the third
autocorrelation constant has a *signed* variant (absolute value inside the maximum,
EV-000004, bound 1.4630716) and a variant with the absolute value outside the maximum, which
benchmark validators score (values near 1.449-1.4557). Numbers from one are not records
for the other. Each entry carries a `conflation_note`, and `SCHEMA.md` explains the rule.

## Badges

Every export also writes [shields.io endpoint](https://shields.io/badges/endpoint-badge) JSON
under `docs/badge/`, so a benchmark README can show whether the value it uses is still current:

| file | message |
|---|---|
| `badge/<id>.json` | `current · 2026-10-12` (green current, yellow unclear, red malformed or a record that fails its definition) |
| `badge/table/<slug>.json` | `N/M current · <date>` for one audited benchmark table |
| `badge/source/<slug>.json` | `N entries · M resolved/exact` for an ingested source table |
| `badge/provenance.json` | `N AI-involved · M definition-checked` |
| `badge/registry.json` | `1034 entries · <date>` |

Replace `<PAGES_BASE>` with the registry's GitHub Pages URL (it changes when the repository
moves to its organisation, so it is not hard-coded here):

```markdown
[![EV-000004](https://img.shields.io/endpoint?url=<PAGES_BASE>/badge/EV-000004.json)](<PAGES_BASE>/entries/EV-000004.html)
[![alphaevolve_v2_paper_audit](https://img.shields.io/endpoint?url=<PAGES_BASE>/badge/table/alphaevolve-v2-paper-audit.json)](<PAGES_BASE>/index.html)
[![registry](https://img.shields.io/endpoint?url=<PAGES_BASE>/badge/registry.json)](<PAGES_BASE>/index.html)
```

Rendered from [`docs/badge/EV-000004.json`](docs/badge/EV-000004.json) as of the last export:

[![EV-000004: current · 2026-10-12](https://img.shields.io/badge/EV--000004-current%20%C2%B7%202026--10--12-green)](docs/badge/EV-000004.json)

`python tools/badges.py` regenerates them alone; `python tools/export.py --out docs` refreshes
them with the pages.

## How to cite

Plain: Thalluri, A. (2026). *Extremal Values Registry* (v0.1.0). Zenodo.
https://doi.org/10.5281/zenodo.23326559 (concept DOI, always the newest version:
https://doi.org/10.5281/zenodo.23326558). To cite one entry: "Extremal Values Registry,
EV-000004 (v0.1.0)". Ids are permanent.

```bibtex
@dataset{thalluri2026extremal,
  author    = {Thalluri, Advatiya},
  title     = {Extremal Values Registry},
  year      = {2026},
  version   = {0.1.0},
  publisher = {Zenodo},
  doi       = {10.5281/zenodo.23326559},
  url       = {https://doi.org/10.5281/zenodo.23326559}
}
```

The derived audit data: https://doi.org/10.5281/zenodo.23324073. A machine-readable
`CITATION.cff` is included.

## How to propose an entry or supersession

1. Write `def.json` (problem family, variant name, definition, direction, normalisation) and
   gather the primary source, a verbatim quote, and a certificate plus verifier if you have one.
2. Run `python tools/propose.py --definition def.json --value V --certificate construction.json --verifier verify.py --citation "..." --url ... --source-date YYYY-MM-DD --quote "..."`.
   It checks identity, strict improvement and the verifier, then writes a ready pull request
   under `proposals/`. It never commits or pushes.
3. Open the pull request with the generated `PR_BODY.md`. CI re-runs everything in a clean
   container. Rules, disputes and review: `CONTRIBUTING.md`. Offline demo:
   `python examples/sample_pr/run.py`.

## Layout

```
schema.json, SCHEMA.md      entry format and field meanings (incl. the conflation note)
data/entries.jsonl          the registry, one entry per line
data/priority_claims.jsonl  priority-claims audit, linked to entry ids
certificates/               construction files and verifiers
tools/                      validate, export, badges, propose, check_freshness, snapshot, ...
examples/quickstart.md      the commands above, with output
tests/                      pytest on fixtures
```

Stdlib only (Python 3.9+); pytest for the tests. See also `DURABILITY.md` (mirrors, weekly
snapshots) and `SUCCESSION.md`.

## Known limits of v0

- 47 entries have `direction: unstated` because the source table does not say; it was not guessed.
- Many definitions still point at the source row instead of stating the functional.
- Only one entry has a certificate here; values are as stated in their sources.

## Licence

Data (`data/`, `certificates/*.json`): CC BY 4.0. Code (`tools/`, `tests/`, verifiers): MIT.
See `LICENSE-DATA` and `LICENSE-CODE`.
