# Verified Value Standard v1

Version 1.0, 2026-10-13. Maintained by the Extremal Values Registry. Licence: CC BY 4.0.
Cite as described in [`CITING.md`](CITING.md).

This standard defines when a claimed value for an extremal problem (a bound, a construction,
a resolution) counts as **verified progress**. It is written so that a benchmark, a
leaderboard, a paper or an AI-mathematics platform can apply it to its own entries and say,
checkably, "this entry meets Verified Value Standard v1".

The key words MUST, MUST NOT and SHOULD are used as in RFC 2119.

## 1. The four checks

A claim meets the standard only when all four checks pass. Each check is recorded with its
date and the evidence it used.

### Check 1: statement fidelity

The problem the claim solves MUST be the problem it is said to solve. The checker compares
the claimed statement (the functional, the domain, the normalisation, the direction, the side
of the bound) against the primary source that defines the problem, and records what was
compared. Two variants that share a name are different problems (see the conflation rule in
`SCHEMA.md`); a value for one is not a record for the other.

Recorded as `fidelity.statement_audit`: `self` (the maintainers transcribed and checked the
statement) or `independent` (a third party audited it). `none` fails the check.

### Check 2: certificate under independent exact re-check

The claim MUST come with a certificate (the construction itself: coefficients, a graph, a
point set, a step function) and a verifier that recomputes the claimed value from the
certificate alone. The re-check MUST:

- run independently of the claimant's own scorer or evaluation code;
- use exact arithmetic (integers, rationals, interval arithmetic with rigorous rounding)
  wherever the value is defined exactly, so that floating-point tolerance cannot carry the
  result;
- check the problem's written constraints (support, feasibility, normalisation), not only
  the objective;
- be reproducible from a pinned file: the certificate's sha256 is recorded, and the verifier
  runs on the Python standard library or another pinned, public environment.

A value whose only support is a platform's own scorer is a sourced claim, not a verified
value.

### Check 3: prior art at the claim date, two passes

The claim MUST be compared against the literature as of the claim date (the first public
appearance of the claimed value). Two search passes are made: a first pass, and a second pass
with reformulated queries (alternative names of the problem, the conflated variants, the
citations of and by the sources found in the first pass). Both passes are recorded with their
dates and sources.

Recorded as `provenance.literature_status`, in the taxonomy of section 4. `unknown` fails the
check: it means the search was not done or did not decide, not that nothing was found.

### Check 4: currentness

At the date of the check, the value MUST be the best known for that variant: no equal or
better value is published elsewhere, and the claim is not superseded. A superseding value
must be strictly better in the entry's direction, for the same variant. Recorded as
`status: current` with `last_checked`. Currentness decays; a check older than 12 months
SHOULD be redone before the entry is cited as current.

## 2. Verdict vocabulary

Values are judged with these words and no others.

| Verdict | Applies to | Meaning |
|---|---|---|
| `VERIFIED` | a value | All four checks pass. |
| `CURRENT` | a table row | The row's value is the best known for its variant at the check date. |
| `STALE` | a table row | A strictly better value was public at the check date. |
| `STALE-LEADERBOARD` | a table row | The row is beaten by a public record on the same leaderboard. |
| `UNCLEAR` | either | The evidence does not decide the question; the reason is recorded. |
| `MALFORMED` | either | The row or claim cannot be scored as written (missing direction, wrong side, ambiguous variant). |
| `NEW` | a priority claim | No equal-or-better value was public before the claim date. |
| `NOT_NEW` | a priority claim | An equal-or-better value was public before the claim date. Sub-classes: `NOT_NEW_SELF_OR_ACKNOWLEDGED` (the earlier value is the claimant's own, or is cited by them) and `NOT_NEW_OTHER` (a third party, not cited). |

A failing verdict states which check failed and links the evidence.

## 3. What "verified" means, and what it does not

**It means:** the stated problem is the intended one; the claimed value is recomputed exactly
from a public certificate by code independent of the claimant; the prior-art status at the
claim date is recorded from two passes; and the value was the best known at the check date.

**It does not mean:**

- that the value is optimal, or that a matching bound exists;
- that the claimant was first (that is a separate priority verdict, `NEW` / `NOT_NEW`);
- that the method behind the value is correct, novel or general;
- that the value stays current after the check date;
- that the prior-art search was exhaustive: two recorded passes reduce, but do not remove,
  the chance of a missed earlier value;
- any judgement about the people, the system or the organisation behind the claim.

## 4. Provenance taxonomy

Every entry records who set the value and what was known.

`provenance.setter_kind`:

- `human`: set by people without reported AI involvement;
- `ai_system`: produced by an AI system, with people only running it;
- `human_ai`: people and an AI system together, as reported by the source;
- `unknown`: the source does not say. It is never guessed.

`provenance.literature_status`, in the taxonomy of the Erdős-problems AI-contributions wiki:

- `known_before`: comparable literature was known before the result;
- `found_after`: comparable literature was found only after the result;
- `unknown`: comparable literature is not known (Check 3 fails).

Plus `first_public_date` and `platform_or_paper`. Provenance describes the claim; it does not
change the verdict on the value.

## 5. Right of reply

Before any failing verdict (`STALE`, `NOT_NEW`, `MALFORMED`, or a failed check) about a
team's claim is published, that team MUST receive the evidence (the source found, the
certificate re-check output, the statement comparison) and **14 days** to reply. The 14 days
run from the date the evidence was sent, and the notice states the planned publication date.
A reply that changes the evidence changes the verdict; the reply, or its absence, is recorded
with the verdict.

## 6. Error-rate reporting

An instrument that issues verdicts (this registry, an audit, a platform applying this
standard) MUST publish its own error rate: the number of verdicts it issued, the number later
reversed (by a reply, a dispute or its own re-check), and the reasons. Reversals stay in the
record and are never deleted. Rates are reported with their denominators, not as percentages
alone.

## 7. Embargo for privately disclosed findings

A finding first disclosed privately to a team (through the right of reply, or a report to a
platform's maintainers) is embargoed: its details are not published until the team has
replied or the agreed review period has ended. During the embargo the public record states
only that a review is under way. The embargo covers the details of the finding, not the
existence of the review.

## 8. Self-certification

A benchmark, platform or paper can certify its own entries against this standard.
Self-certification is a claim that anyone can re-check, and the registry treats it as one.

Checklist, per entry:

- [ ] The statement is written out in full (functional, domain, normalisation, direction,
      side) and compared with its primary source; the comparison is recorded.
- [ ] A certificate file is public, its sha256 is recorded, and a verifier independent of the
      claimant's scorer recomputes the value with exact arithmetic and checks the constraints.
- [ ] Two prior-art passes at the claim date are recorded with dates and sources;
      `literature_status` is not `unknown`.
- [ ] The value is current at a stated check date; superseded values are listed with sources.
- [ ] Provenance is filled in (`setter_kind`, `literature_status`, `first_public_date`,
      `platform_or_paper`).
- [ ] Any failing verdict about another team's claim went through the 14-day right of reply.
- [ ] The instrument's verdict count and reversal count are published.

Machine check. Write the entries in the registry format (`schema.json`, one JSON object per
line), set `"standard_version": "1.0"` on each entry that claims the standard, and run:

```
python tools/validate.py --entries your_entries.jsonl --claims your_claims.jsonl --root .
```

For entries that declare `standard_version`, `validate.py` requires `fidelity.statement_audit`
`self` or `independent`; a certificate file with a matching sha256, `verifier_kind: exact` and
a `verifier_command` whose output equals the registered value; `provenance.literature_status`
other than `unknown`; and `status: current`. It exits 0 when every entry passes. The machine
check covers what can be checked mechanically; the prior-art passes and the right of reply are
checked by reading the recorded evidence.

To have entries listed in the registry, open a pull request as described in
`CONTRIBUTING.md`; CI re-runs the same command in a clean container.

## 9. Versioning

This is version 1.0. A later version gets a new number; entries keep the version they were
certified under, and the requirements of a published version do not change.
