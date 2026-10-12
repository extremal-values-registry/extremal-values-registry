# Durability

The registry must outlive any one host, account or maintainer.

## Governance

The definition fields (`definition`, `domain`, `direction`, `units_or_normalisation`) and
the verifiers are the canonical truth, not any person. A value stands because its verifier
reproduces it or its primary source states it; it falls when the verifier fails or the
source does not say it. No maintainer, reviewer or contributor can overrule a verifier
result or redefine an entry, and anyone with a clean machine can re-check every claim
(`SUCCESSION.md`).

## Copies

| copy | what | how it is kept current |
|---|---|---|
| primary git host | the repository and its pull requests | contributors |
| second git remote (a different provider) | a full mirror (`git push --mirror`) | `snapshot.yml` weekly, when the `MIRROR_URL` secret is set |
| Zenodo | one versioned DOI per weekly release; a concept DOI that always resolves to the latest | the Zenodo GitHub integration archives every release `snapshot.yml` creates |
| Software Heritage | permanent source archive with intrinsic identifiers (SWHIDs) | `snapshot.yml` requests a save of the origin weekly; anyone can request one at archive.softwareheritage.org |
| snapshot archives | `registry-<date>.tar.gz` + `.manifest.json` (sha256 of every file) | `tools/snapshot.py`, attached to each release |

One-time setup for a new host: enable the Zenodo integration for the repository; add the
`MIRROR_URL` secret (an authenticated URL of the second remote); add the `LITERATURE_KEY`
secret (an OpenAlex key or contact address) for the PR literature passes; protect `main`
with "require checks validate, verifiers, literature" and "require 1 approving review".

## Weekly snapshot

```
python tools/snapshot.py --out snapshots [--keep 12]
```

It validates first (every verifier runs) and refuses to snapshot a failing tree. The
archive is reproducible: sorted members, zeroed times and owners, so the same tree gives
the same sha256 and any copy can be checked against the manifest. It never overwrites an
existing date. `.github/workflows/snapshot.yml` runs it every Monday and publishes the
release; run it by hand from any clone if the host's scheduler is gone.

## Restoring

From any copy: unpack (or clone), then `python tools/validate.py` and
`python -m pytest -q`. A copy is good when both exit 0 and the archive's sha256 matches
its manifest. If copies disagree, the newest one that validates and whose history contains
the others wins; differences are resolved by the verifiers, per Governance.
