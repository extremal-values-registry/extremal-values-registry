# Extremal values registry (v0)

A registry of best-known values for extremal problems: one entry per problem **variant**,
holding the exact definition, the current best value, the construction or certificate,
the verifier, the date and primary source, and the chain of values it superseded. Think of
OEIS, but for best-known bounds. Each entry has a stable id (`EV-000001`, ...) and lists the
names that benchmarks and leaderboards use for the same variant, so a benchmark can pin
an entry id instead of copying a number that goes stale.

Version 0 comes from a published literature audit of five "best known" tables (two
AlphaEvolve result sets, HorizonMath, the Optimization Constants in Mathematics table,
EinsteinArena). Every audited row is either an entry or an alias of one. Where the audit
found a row stale, the entry holds the audited value and the listed value is in
`superseded[]`. The audit's priority-claims table is in `data/priority_claims.jsonl`, with
each claim linked to entry ids where the variant is identified. One entry (the
maximum-of-absolute-value third autocorrelation constant, EV-000004) carries an exact
certificate and verifier in this repository.

**An entry is a fact only when its verifier passes. Until then it is a sourced claim.**

## Citation and DOI

Concept DOI (always the newest version): https://doi.org/10.5281/zenodo.23326558
Version 0.1.0 DOI (exact values as published 2026-10-13): https://doi.org/10.5281/zenodo.23326559
Derived from the audit data at https://doi.org/10.5281/zenodo.23324073.

## Layout

```
schema.json, SCHEMA.md      entry format and field meanings (incl. the conflation note)
data/entries.jsonl          the registry, one entry per line
data/priority_claims.jsonl  priority-claims audit, linked to entry ids
certificates/               construction files and verifiers
tools/validate.py           schema, id uniqueness, sha256, runs every verifier
tools/export.py             CSV + static HTML index (dist/)
tools/check_freshness.py    rows CSV (freshcheck format) -> proposed diff, never silent writes
tools/seed_from_audit.py    how v0 was built from the audit tables (--src <dir>)
tests/                      pytest on fixtures
```

```
python tools/validate.py                      # exit 0 when every check and verifier passes
python tools/export.py --out dist             # dist/entries.csv, dist/index.html, dist/entries/*.html
python tools/check_freshness.py rows_2026-11-01.csv          # prints a diff, writes nothing
python tools/check_freshness.py rows_2026-11-01.csv --apply  # writes after printing the diff
python -m pytest -q
```

Stdlib only (Python 3.9+); pytest for the tests.

## How to cite an entry

Cite the id and the registry version, e.g. "Extremal values registry, EV-000004 (v0,
checked 2026-10-12)". Ids are permanent. A superseded value stays in the entry's chain; an
entry found to merge two variants is split into new ids, and the old id's notes point to them.

## Proposing an entry or a supersession

Short version: `python tools/propose.py ...` builds a checked pull request for you; see
`CONTRIBUTING.md` (rules, merge requirement, disputes), `DURABILITY.md` (mirrors, weekly
snapshots, governance) and `SUCCESSION.md` (running everything from a clean machine).
The manual route:

Open a pull request that changes `data/entries.jsonl` and includes:

1. **Source**: citation, URL and date of the primary source (paper PDF, canonical table, or
   the authors' own paper), with a verbatim quote of the value in `notes`.
2. **Certificate**: the construction (or proof certificate) under `certificates/<name>/`,
   with its sha256 in the entry.
3. **Verifier**: a command that prints the value from the certificate; exact arithmetic
   where possible (`verifier_kind: exact`), otherwise a stated tolerance.
4. A passing `python tools/validate.py` and `python -m pytest -q`.

A supersession must be strictly better in the entry's direction and for the same variant
(same functional, domain and normalisation). If it is a different variant, propose a new
entry and add a conflation note to both. Literature checks in the freshcheck row format can
be turned into a proposed diff with `tools/check_freshness.py`.

## Verdict standard

- **STALE** (a supersession) needs one of: (a) a verbatim quote of the better value from a
  primary source that was opened (paper PDF, canonical table, authors' own paper), with URL
  and date; or (b) a public construction re-scored offline with the benchmark's own
  validator, with the command and output saved (recorded as `value_kind: record`).
- A snippet, abstract-only hit, blog, tweet or leaderboard cell alone is **STALE-LEADERBOARD**
  or **UNCLEAR**, never STALE; it does not change `current_value`.
- **MALFORMED**: the listed value is not a scoreable best-known value (a proven bound stored
  as a target, a range string, a count).
- **UNCLEAR**: primary source unreachable, unrefereed claim to a major open problem, or
  conflicting sources.
- **CURRENT**: no superseding primary source found by two independent passes.
- "Better" means strictly better in the variant's direction; equal is CURRENT.

## Known limits of v0

- 47 entries have `direction: unstated` because the source table does not say and it was
  not inferred by guessing. Many `source_label` definitions still point to the source row
  instead of stating the functional; transcribing them is the main v0 to v1 task.
- Only one entry has a certificate here; all other values rest on their cited sources
  (`verifier_kind: external`).
- Values are as stated in the sources: closed forms and qualified statements are strings.

## Licence

Data (`data/`, `certificates/*.json`): CC BY 4.0. Code (`tools/`, `tests/`, verifiers): MIT.
See `LICENSE-DATA` and `LICENSE-CODE`.
