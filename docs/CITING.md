# Citing the registry

The registry is archived on Zenodo. Use the **concept DOI**
general (it always resolves to the newest version), and a **version DOI** (for v0.1.0,
matter. Entry ids (`EV-NNNNNN`) are permanent and never reused.

## The registry

Extremal Values Registry maintainers (2026). *Extremal Values Registry*. Zenodo.

```bibtex
@dataset{evr2026,
  author    = {{Extremal Values Registry maintainers}},
  title     = {Extremal Values Registry},
  year      = {2026},
  publisher = {Zenodo},
}
```

For a specific release, add `version = {v2026.10.13}` (the tag you used) and that release's
version DOI.

## One entry

Values change, so cite the id, the release and the access date:

> Extremal Values Registry, entry EV-000004, release v2026.10.13 (accessed 2026-10-13).

In a table, a `registry_id` column holding `EV-000004` is enough, with the registry cited once.

## A verdict

Verdicts (`VERIFIED`, `CURRENT`, `STALE`, `NEW`, `NOT_NEW`, ...; see
[`STANDARD.md`](STANDARD.md)) are dated. Cite the verdict, the entry or claim id, the check
date and the standard version:

> EV-000004: VERIFIED under Verified Value Standard v1.0, checked 2026-10-12
> (Extremal Values Registry, release v2026.10.13).

For the priority-claims audit, cite the claim id (for example `AENB-01`) and the audit

## The standard

> Extremal Values Registry (2026). *Verified Value Standard v1.0*. docs/STANDARD.md in the

## CITATION.cff

`CITATION.cff` at the repository root is read by GitHub ("Cite this repository") and Zenodo.

| field | value |
|---|---|
| `cff-version` | `1.2.0` |
| `title` | `Extremal Values Registry` |
| `version` | the release |
| `doi` | the version DOI of that release |
| `date-released` | the release date |
| `authors` | family and given names |
| `license` | `MIT` (code) and `CC-BY-4.0` (data) |
| `repository-code` | the GitHub URL |
| `abstract` | one sentence |
