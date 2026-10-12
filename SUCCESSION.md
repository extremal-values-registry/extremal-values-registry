# Succession: running the whole loop from a clean machine

For any future maintainer or agent. Nothing here needs a particular person, account or
paid service.

## Prerequisites

- Python 3.9 or later (stdlib only for every tool) and `pip install pytest`.
- git. Docker only if you want to reproduce the clean-container verifier step exactly.
- Optional: an OpenAlex key or contact address in `LITERATURE_KEY` for the literature
  passes (free). Without it they label instead of searching.

## Get the registry

Clone any copy in `DURABILITY.md` (primary host, second remote, Software Heritage), or
unpack the newest `registry-<date>.tar.gz` from the Zenodo concept DOI and check its sha256
against the manifest.

## Check it

```
python tools/validate.py          # 0 = schema, ids, aliases, sha256, every verifier pass
python -m pytest -q               # 0 = tools behave as documented
python examples/sample_pr/run.py  # 0 = propose -> PR checks loop works end to end
```

## The loop

| step | command | state it changes |
|---|---|---|
| propose an entry or supersession | `python tools/propose.py ...` | writes `proposals/<branch>/` only |
| check a pull request locally | `python tools/dry_run_pr.py --base <main's entries.jsonl>` | none |
| check a pull request in CI | `.github/workflows/verify.yml` (automatic) | PR labels, check summary |
| literature passes | `python tools/literature_check.py --ids EV-...` | writes a rows CSV |
| apply a literature check | `python tools/check_freshness.py rows_<date>.csv [--apply]` | `data/entries.jsonl` with `--apply` |
| publish the site | `python tools/export.py --out dist` | `dist/` |
| weekly snapshot | `python tools/snapshot.py --out snapshots` (or `snapshot.yml`) | `snapshots/`, a release |

## Where state lives

- `data/entries.jsonl`: the registry; one entry per line; ids permanent.
- `data/priority_claims.jsonl`: the priority-claims audit, linked to entry ids.
- `certificates/<name>/`: constructions and verifiers; sha256 recorded in each entry.
- `schema.json`, `SCHEMA.md`: the entry format; `CONTRIBUTING.md`: the rules.
- Git history and pull requests: who changed what, with check output.
- Releases, Zenodo, Software Heritage, the second remote: the copies.
Nothing else holds state: no database, no server, no private notes.

## Taking over

1. Check it (above). If something fails on a fresh clone, fix it in a pull request first.
2. Get admin on the primary host, or, if that is impossible, promote the second remote to
   primary and add a new mirror; update `DURABILITY.md` in a pull request.
3. Re-create the secrets (`LITERATURE_KEY`, `MIRROR_URL`) and branch protection.
4. Review pull requests by the merge rule in `CONTRIBUTING.md`. The definition fields and
   the verifiers decide; you confirm that they were run.
