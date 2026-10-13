# Entry schema (v1)

One JSON object per line in `data/entries.jsonl`. The machine-readable form is
`schema.json`; `python tools/validate.py` enforces it. One entry is one problem **variant**:
two statements that differ in the functional, the domain, the normalisation or the
direction are two entries, even when the literature gives them one name.

| field | type | meaning |
|---|---|---|
| `id` | `EV-NNNNNN` | Stable identifier. Never reused, never renumbered. Cite this. |
| `problem_family` | string | Grouping only (e.g. "Autocorrelation inequalities"). |
| `variant_name` | string | Human name of this exact variant. |
| `definition.text` | string | The exact functional or statement in plain text. |
| `definition.latex` | string | The same in LaTeX (may be empty while `status` is `source_label`). |
| `definition.status` | `curated` \| `source_label` | `curated`: transcribed and checked against the sources. `source_label`: v0 placeholder that points to the source row; the exact functional is still to be transcribed. |
| `domain` | string | Where the optimisation runs (function class, point sets, rings, ...). |
| `direction` | `min` \| `max` \| `unstated` | Which way is better. `unstated` when the source table does not say and it could not be inferred without guessing. |
| `units_or_normalisation` | string | Units, scaling, squared vs unsquared, etc. |
| `current_value` | number \| string \| null | Best value under the verdict standard. A string holds closed forms or ranges that are not a single float. `null` when no scoreable value exists. |
| `value_kind` | `bound` \| `exact` \| `record` \| `status` | `bound`: a proven or constructed one-sided bound. `exact`: the true value is known. `record`: best value attained by a public construction re-scored with a validator, not yet in a primary paper. `status`: the value is `resolved` or `open` (used for problems whose answer is a statement, not a number); `direction` is then `unstated`. |
| `certificate.file` | path \| null | Construction or proof certificate inside `certificates/`. |
| `certificate.sha256` | hex \| null | SHA-256 of that file; `validate.py` recomputes it. |
| `certificate.verifier_command` | string \| null | Command, run from the repository root, that prints the value. |
| `certificate.verifier_kind` | `exact` \| `numeric` \| `external` | `exact`: rational/interval arithmetic, tolerance 1e-12 by default. `numeric`: floating point, tolerance stated. `external`: no certificate here, the value rests on the cited source. |
| `certificate.verified_date` | date \| null | Last date the verifier was run and passed. |
| `certificate.value_pattern`, `tolerance`, `verifier_file` | optional | Regex with one group that extracts the value from verifier output; absolute tolerance; the verifier script's path. |
| `source` | `{citation, url, date, refereed}` | Primary source of the current value. `refereed` is true only when the audit notes say so. |
| `superseded` | list of `{value, source, url, date}` | Earlier or stale values for this variant, worst first. Values listed by benchmarks that the audit found stale are here, with the benchmark named as the source. |
| `aliases` | list of `{scheme, id, side?, ranking_number?, audit_table?, audit_verdict?}` | Names used elsewhere: `HorizonMath` problem id, `OptimizationConstants` table id (with `side` lower/upper), `EinsteinArena` problem slug or title (with `ranking_number`), `AlphaEvolve-notebook` / `AlphaEvolve-v2-paper` row ids, `ErdosProblems` problem number, `DS1` cell (e.g. `R(5,5)`), `PackingCenter` cell (`<table> n=<n>`, e.g. `cirinsqu n=7`), `Cohn` cell (`kissing-numbers d=<n>` or `sphere-packing d=<n>`, with `side` when it names one bound of a cell). No alias may belong to two entries. |
| `status` | `current` \| `unclear` \| `malformed` | `unclear`: conflicting sources, unreachable primary source, or unrefereed claim to a major problem. `malformed`: the source row is not a scoreable best-known value. |
| `last_checked` | date | Last literature check (see `tools/check_freshness.py`). |
| `conflation_note` | string \| null | Present when the literature or benchmarks confuse this variant with another. |
| `notes` | string \| null | Audit notes carried over from the source tables. |
| `provenance.setter_kind` | `human` \| `ai_system` \| `human_ai` \| `unknown` | Who set the current value. `unknown` whenever the source does not say; it is never guessed. |
| `provenance.literature_status` | `unknown` \| `found_after` \| `known_before` | The taxonomy of the Erdős-problems AI-contributions wiki: comparable literature not known; found only after the result; known before it. |
| `provenance.first_public_date` | `YYYY[-MM[-DD]]` \| null | First public appearance of the current value or resolution. |
| `provenance.platform_or_paper` | string \| null | Where it appeared (paper, platform, leaderboard). |
| `provenance.verification_state`, `basis`, `records` | optional | The source's own verification colour (`full`, `partial`, `incorrect`, `unverified`); how the fields were derived; for wiki-derived entries, every wiki row (section, date, AI systems, outcome, colour). |
| `fidelity` | object \| null | Present when the entry has a formal statement (always for `definition.status: curated`; also when a Lean formalisation is reported). `statement_audit`: `none` \| `self` (maintainers transcribed and checked it) \| `independent` (a third party audited the statement against the source); `audit_note` says what was compared. |
| `feasibility` | object \| null | Definition-level check of the records behind the value. `definition_checked` (bool); `check_source` (the public data the check ran on); optional `check_date`, `result` (`feasible` \| `infeasible` \| `score_not_reproduced` \| `not_checked`), `records_checked`, `records_infeasible`, `records_not_reproduced`, `note`. A record is checked against the problem's written definition, independently of the platform's scorer. |

## Conflation note

Variants that share a name are where tables go wrong, so an entry records the confusion
explicitly. Example, the third autocorrelation inequality for signed f on [-1/4,1/4]:

- **EV-000003**: ratio |max_t (f*f)(t)| / (int f)^2 (absolute value outside the maximum). This is
  what the public validators score; current 1.4491219518523413.
- **EV-000004**: ratio max_t |(f*f)(t)| / (int f)^2 (maximum of the absolute value);
  current 1.4630715826075593 with an exact certificate; previous 1.4688.

The 2025 results notebook names the first C3 (1.4557) and the second C3' (1.4688); the later v2
paper names the second "6.4(a)" (unprimed) and the first "6.4'". A table that copies names
across the two sources swaps the variants. A value for one does not bound the other.
Each entry's `conflation_note` points at the other.

## Merging rule

Rows from different tables merge into one entry only when they state the same functional,
domain, normalisation and direction. Equal names are not enough. When unsure, keep separate
entries and write a conflation note (as for the uncertainty and prime-number-theorem
formulations, whose arena values are not comparable with the v2-paper values as stated).

## Provenance, fidelity and feasibility

Three questions a value table usually cannot answer: who found the value (and did the
literature already have it), is the stated problem the intended problem, and does the record
behind the value satisfy the definition rather than just the scorer. `tools/validate.py`
enforces the cross-field rules: a `status` value is `resolved` or `open` with direction
`unstated`; a curated definition carries a `fidelity` record; a checked `feasibility` names its
`check_source` and a `result`; an unchecked one has no positive result.

Ingested source tables:

- **Erdős problems, AI contributions wiki** (frozen 2026-06-30): `tools/ingest_erdos_wiki.py`.
  One entry per problem. `resolved` means the wiki records a full resolution (a green row that is
  not about a variant, an extension or one part); `open` means it records none, which is not a
  claim that the problem is open in the literature. Section 1(a)/(b)/(c) give `ai_system` with
  literature `unknown`/`found_after`/`known_before`; 1(d) gives `human_ai`; section 2 (literature
  search, formalisation, rewriting, computation) gives `human`, with `known_before` when an
  earlier proof was found, formalised or rewritten.
- **Radziszowski, Small Ramsey Numbers (DS1), Tables Ia and Ib**: `tools/ingest_ds1.py`. One entry
  per cell R(k,l), 3 <= k <= l. Exact cells are `exact`; the rest are `"L <= R(k,l) <= U"`
  strings (`?` where the table gives no bound). When Table Ib improves a Table Ia upper bound, the
  Table Ia bound is in `superseded`.
- **Erich Friedman's Packing Center** (circles in squares, circles in circles, equilateral
  triangles in squares; squares in squares from David Ellsworth's updated table that the Packing
  Center links): `tools/ingest_packing_center.py`. One entry per n <= 50 with a value. Cells the
  page marks "Proved" or "Trivial." are `exact`, the rest `record`. Truncated decimals are kept as
  printed, as strings ending in `+` (the true value is slightly larger). Record holder and date are
  quoted in `provenance.basis`; `first_public_date` is the date of the first clause.
- **Henry Cohn's tables of kissing numbers and sphere packing densities**: `tools/ingest_cohn.py`.
  One entry per dimension 1..48. Proved rows (one value for both bounds) are `exact`; the rest
  are `"L <= tau_n <= U"` / `"L <= Delta_n <= U"` strings as printed. Cells the registry already
  held (kissing d = 5, 6, 9, 11; density d = 10) get a `Cohn` alias and a `conflation_note`
  instead of a new entry; density d = 12 is a new entry cross-linked to the lattice-only entry.
