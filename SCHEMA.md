# Entry schema (v0)

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
| `value_kind` | `bound` \| `exact` \| `record` | `bound`: a proven or constructed one-sided bound. `exact`: the true value is known. `record`: best value attained by a public construction re-scored with a validator, not yet in a primary paper. |
| `certificate.file` | path \| null | Construction or proof certificate inside `certificates/`. |
| `certificate.sha256` | hex \| null | SHA-256 of that file; `validate.py` recomputes it. |
| `certificate.verifier_command` | string \| null | Command, run from the repository root, that prints the value. |
| `certificate.verifier_kind` | `exact` \| `numeric` \| `external` | `exact`: rational/interval arithmetic, tolerance 1e-12 by default. `numeric`: floating point, tolerance stated. `external`: no certificate here, the value rests on the cited source. |
| `certificate.verified_date` | date \| null | Last date the verifier was run and passed. |
| `certificate.value_pattern`, `tolerance`, `verifier_file` | optional | Regex with one group that extracts the value from verifier output; absolute tolerance; the verifier script's path. |
| `source` | `{citation, url, date, refereed}` | Primary source of the current value. `refereed` is true only when the audit notes say so. |
| `superseded` | list of `{value, source, url, date}` | Earlier or stale values for this variant, worst first. Values listed by benchmarks that the audit found stale are here, with the benchmark named as the source. |
| `aliases` | list of `{scheme, id, side?, ranking_number?, audit_table?, audit_verdict?}` | Names used elsewhere: `HorizonMath` problem id, `OptimizationConstants` table id (with `side` lower/upper), `EinsteinArena` problem slug or title (with `ranking_number`), `AlphaEvolve-notebook` / `AlphaEvolve-v2-paper` row ids. No alias may belong to two entries. |
| `status` | `current` \| `unclear` \| `malformed` | `unclear`: conflicting sources, unreachable primary source, or unrefereed claim to a major problem. `malformed`: the source row is not a scoreable best-known value. |
| `last_checked` | date | Last literature check (see `tools/check_freshness.py`). |
| `conflation_note` | string \| null | Present when the literature or benchmarks confuse this variant with another. |
| `notes` | string \| null | Audit notes carried over from the source tables. |

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
