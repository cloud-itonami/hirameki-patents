# hirameki-patents — public-patent corpus

> hirameki 閃き · ADR-2606212200 · **PUBLIC patent bibliographic data only** ·
> aggregate-first · no person-level inventor data (G6) · supersedes the legacy
> RisingWave/B2 patent pipeline (ADR-2604251024).

The DataLad dataset substrate (DataLad + git-annex + IPFS, ADR-2605241500) for the
**hirameki** world public-patent KG-mirror. Holds the patent CORPUS as canonical
kotoba EDN, each artifact content-addressed to a CIDv1 (raw, sha2-256) **byte-identical
to `ipfs add --cid-version=1 --raw-leaves`** and verifiable with or without the `ipfs`
daemon.

## Artifacts

| artifact | file | what |
|---|---|---|
| corpus | `hirameki-patents.corpus.kotoba.edn` | normalized patent records (sorted by id, deterministic) |
| datoms | `hirameki-patents.datoms.kotoba.edn` | the same corpus as kotoba EAVT `[:db/add e a v]` |
| manifest | `publish-manifest.edn` | per-artifact bytes + CID + single-block flag |
| provenance | `ingest-provenance.edn` | ingest id, sources, counts |

CIDs live in `publish-manifest.edn` and are verified with `bb verify`.

## Scope (R0 vs full corpus)

- **R0 (this snapshot)**: a BOUNDED `:representative` slice across CPC sections, git-tracked
  directly (no git-lfs, single raw block each). This is what ships in the repo.
- **Full world corpus (~200M public patents)**: the operator **G9** step — bulk pull of
  USPTO PatentsView (CC0, weekly TSV) / EPO OPS (free tier) / WIPO PATENTSCOPE, materialized
  here and pushed via **DataLad → IPFS (git-annex)** (the >256 KiB artifacts chunk into a
  UnixFS dag-pb tree; the bounded snapshot stays inline). The loop never queries the API —
  the snapshot is the single source of truth (G8/G9, no-server-key).

## Fetch + verify (trustless, no daemon trust)

```bash
# re-content-address the local snapshot — must equal the manifest CID
bb verify
# or with the daemon:
ipfs add -Q --cid-version=1 --raw-leaves --only-hash hirameki-patents.corpus.kotoba.edn
```

## Sources (license)

| source | license | role |
|---|---|---|
| USPTO PatentsView | CC0 | granted-patent bibliographic bulk (TSV) |
| EPO OPS REST | free tier | citation / family / INPADOC cross-link |
| WIPO PATENTSCOPE | free API | PCT international applications |

Public bibliographic metadata only — never paid terminals (Rider §2(e)); a RELEASE map,
never an FTO / infringement / patent-equity tool (G1).
