# Supersede EV-000004: Third autocorrelation constant, signed f, maximum of the absolute value = 1.4630715826075593

Kind: supersede. Branch: `propose/EV-000004-2026-10-12`.

Source: This registry, certificate certificates/third_autocorrelation_abs_inside (300-cell step function; exact rational evaluation) (no url, 2026-10-12). Quote: "C(f) = 1.4630715826075593 (exact rational)"

Checks run by tools/propose.py on 2026-10-12:

- verifier (isolated): PASS, prints 1.4630715826075593
- identity rule: OK
- validate: OK

To open the pull request from a clone of the registry:

```
git checkout -b propose/EV-000004-2026-10-12
git apply -p1 examples/sample_pr/proposal/propose_EV-000004-2026-10-12/proposal.patch
python tools/validate.py && python -m pytest -q
git add data/entries.jsonl certificates/third_autocorrelation_abs_inside
git commit -m "Supersede EV-000004: Third autocorrelation constant, signed f, maximum of the absolute value = 1.4630715826075593"
git push -u origin propose/EV-000004-2026-10-12   # then open the PR
```

Review: one approving review plus green `verify` checks (CONTRIBUTING.md).
