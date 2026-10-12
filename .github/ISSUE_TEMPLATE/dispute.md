---
name: Dispute an entry
about: Challenge a value, a definition, a merge of two variants, or a source
title: "Dispute EV-NNNNNN: <one line>"
labels: dispute
---

**Entry id:** EV-NNNNNN

**What is disputed** (tick one)
- [ ] The value: the verifier does not reproduce it, or the certificate is invalid
- [ ] The definition does not match the cited source (functional, domain, normalisation, direction)
- [ ] Two variants are merged in this entry (conflation)
- [ ] A better value exists (use `tools/propose.py` instead if you have a certificate or a primary quote)
- [ ] The source is not primary, or the quote is not in it

**Evidence** (at least one; the dispute is decided on this, not on who files it)
- Command and full output, e.g. `python tools/validate.py` or the entry's `verifier_command`:
- Primary source URL, date, and the verbatim quote:
- For a conflation: the two statements side by side, and which aliases belong to which:

**Proposed resolution**
- [ ] Move `current_value` to `superseded[]` and restore the previous value
- [ ] Split into new entries with conflation notes on both
- [ ] Correct the source or quote
- [ ] Other:

**Checks I ran** (paste output)
```
python tools/validate.py
python -m pytest -q
```
