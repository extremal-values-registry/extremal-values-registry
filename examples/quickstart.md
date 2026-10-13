# Quickstart

Python 3.9+, standard library only. Run from the repository root.

## 1. Validate the whole registry

```
python tools/validate.py
```

```
799 entries, 1 with certificates, 231 claims: OK
```

Checks the schema, id uniqueness, alias uniqueness, the sha256 of every certificate, and
re-runs every verifier. Exit code 0 means everything passed.

## 2. Export a CSV and a static site

```
python tools/export.py --out dist
```

```
exported 799 entries to dist
```

Writes `dist/entries.csv`, `dist/index.html` and one page per entry in `dist/entries/`.
(Use `--out` with a scratch directory if you do not want to touch the committed `dist/`.)

## 3. Check the one exact certificate yourself

```
python -I certificates/third_autocorrelation_abs_inside/verify.py certificates/third_autocorrelation_abs_inside/construction.json
```

```
n = 300  int f = 0.0016666666666666666  max|f*f| = 4.064087729465442e-06
C(f) = 1.4630715826075593  (exact rational: 2039224160683882663565441886346340189798400 / 1393796574908163689489385839036226787118881 )
upper bound C <= 1.4630715826075593 ; previous best published 1.4688; improvement: True
```

The construction is a 300-cell step function; its maximum autoconvolution is attained at a
knot, so the printed ratio is exact for the stored function. This is the registry's
definition of a fact: the value is reproduced from the certificate, not copied from a page.

## 4. Propose a change

See the end-to-end offline demo: `python examples/sample_pr/run.py`, and `CONTRIBUTING.md`.
