# Contributing

Anyone, person or agent, can add an entry or supersede a value without the maintainer. The
checks decide; a reviewer confirms that the checks are the right checks.

## The fast path

```
python tools/propose.py --definition def.json --value V \
    --certificate construction.json --verifier verify.py \
    --citation "Authors, title" --url https://... --source-date YYYY-MM-DD \
    --quote "verbatim sentence giving the value" [--entry EV-NNNNNN]
```

`def.json` holds `problem_family`, `variant_name`, `definition {text, latex, status}`,
`domain`, `direction`, `units_or_normalisation` (optionally `aliases`, `conflation_note`).
The tool runs the verifier on the certificate in isolation, checks the identity rule and
strict improvement, validates the whole tree, and only then writes
`proposals/<branch>/` with `proposal.patch`, `files/`, `entry.json` and `PR_BODY.md`.
Follow the commands in `PR_BODY.md` to open the pull request. It never commits or pushes.

To see the whole loop offline: `python examples/sample_pr/run.py` (the signed
third-autocorrelation certificate, EV-000004, from proposal to green checks).

## What a pull request must pass (`.github/workflows/verify.yml`)

1. `tools/validate.py`: schema, unique ids, unshared aliases, sha256 of every certificate,
   every verifier reproduces its registered value.
2. `tools/pr_checks.py identity`: the identity rule below, strict improvement, and the old
   value recorded in `superseded[]`.
3. `tools/pr_checks.py verify`: every changed entry's `verifier_command`, re-run on its
   certificate in a clean container with no network and only the certificate directory.
4. `tools/literature_check.py`: two independent passes (OpenAlex, then arXiv) for work dated
   after the source. Free indexes only. Without the `LITERATURE_KEY` repository secret the
   PR is labelled `needs-literature-check` instead of failing; with candidates it is
   labelled `literature-candidates` and a reviewer opens them.
5. `python -m pytest -q`.

`python tools/dry_run_pr.py --base <entries.jsonl of main>` runs the same steps locally
(`act pull_request` also works if you have Docker).

**Merge rule:** all three jobs green and one approving review. The reviewer checks the
quote against the opened source and that the definition matches the source's statement;
the reviewer does not re-derive the value, the verifier does. A reviewer may not approve
their own proposal. A `needs-literature-check` label must be cleared by a two-pass rows file
(below) before merge.

## The two-pass rule

A value is CURRENT only when two independent passes found no superseding primary source.
A supersession (STALE) needs either (a) a verbatim quote of the better value from a primary
source that was opened (paper PDF, canonical table, authors' own paper), with URL and date,
or (b) a public construction re-scored with a verifier in this repository. A snippet,
abstract-only hit, blog, tweet or leaderboard cell is STALE-LEADERBOARD or UNCLEAR and never
changes `current_value`. Record passes as rows in the freshcheck format and turn them into a
diff with `tools/check_freshness.py rows_YYYY-MM-DD.csv` (prints, writes nothing without
`--apply`). The automated passes only find candidates; they never write STALE.

## The identity rule: the definition is the identity

An entry is the tuple (`definition.text`, `domain`, `direction`, `units_or_normalisation`).
Same tuple, same entry; a different tuple is a different entry, whatever the name. So:

- A pull request may not change those fields of an existing id (one exception: replacing a
  `source_label` placeholder definition with a transcribed, `curated` one).
- Ids are never removed or renumbered. An entry found to merge two variants is split into
  new ids, and the old id's notes point to them.
- A better value is a supersession only if it is for the same tuple and strictly better in
  the entry's direction. Equal is CURRENT.

## The conflation note rule

When the literature or a benchmark uses one name for two variants (squared vs unsquared,
absolute value inside vs outside the maximum, different normalisation), propose a separate
entry and set `conflation_note` on **both** entries, each naming the other id, the names
each source uses, and the fact that a value for one does not bound the other. See the
EV-000003 / EV-000004 example in `SCHEMA.md`. When unsure whether two rows are the same
variant, keep them separate and write the note.

## Disputes

Open an issue with `.github/ISSUE_TEMPLATE/dispute.md`. A dispute is settled by the
verifier and the definition fields, not by who files it: a value whose verifier fails is
removed from `current_value` (it moves to `superseded[]` with a note); a definition shown to
mismatch its source is split per the identity rule.
