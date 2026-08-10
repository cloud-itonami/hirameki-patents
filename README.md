# hirameki-patents — public-patent corpus

> hirameki 閃き · **PUBLIC patent bibliographic data only** · aggregate-first ·
> no person-level inventor data (G6) · a RELEASE map, never an FTO/infringement
> verdict (G1) · ADR-2606212200, ADR-2607251552

The **data** half of hirameki. The actor that fills it lives in
[`cloud-itonami/hirameki`](https://github.com/cloud-itonami/hirameki); this repo
is versioned independently so the corpus can be cited, fetched and verified
without the code that produced it.

## What is in here right now (measured 2026-08-10)

| | |
|---|---:|
| patents | **633** (626 harvested + 7 curated) |
| citation edges | 2,448 |
| distinct cited ids | 1,945 — of which **1,323 are still unharvested frontier** |
| jurisdictions | 10 (US 350, JP 145, EP 49, WO 39, GB 28, DE 7, …) |
| named assignees | 292 · named-HHI **0.013** |
| CPC classification | **absent** — see below |

<sub>An earlier version of this table said 20 jurisdictions. It was wrong — the
number had been read off the head of a list rather than counted. It is 10.</sub>

**This is a citation-graph neighbourhood, not a sample.** It was grown by walking
outward from four seed patents (CRISPR-Cas9 ×2, an aqueous coating composition,
mRNA-LNP), so its shape reflects those seeds: Kansai Paint is the top assignee at
7.3% because one seed was a paint patent, not because coatings dominate the
patent system. Against ~200M public patents worldwide that is 0.0003% coverage.
`ingest-provenance.edn` states this per source; no aggregate here should be read
as a world statistic.

## What this corpus cannot answer

A Google Patents page carries no CPC symbol. So there is **no field-level
concentration** in this data — rows carry `:field "UNKNOWN"` rather than a value
inferred from the title, and hirameki's CPC analytics run only on the curated
seed. The leg that would supply CPC (USPTO ODP) is implemented and
fixture-tested but has never been run against the live API; it needs a free
operator key. That is recorded as `:operator-step-not-yet-run`, not as coverage.

## Layout

| path | what |
|---|---|
| `80-data/public/google-patents.NNNN.journal.edn` | the harvest journal — append-only `[e a v tx op]` quads, one per line, sealed at 1 MiB per shard. **The input, and the authoritative record** (ADR-2607072300) |
| `corpus/NNN.kotoba.edn` | normalized patent rows, sorted by id |
| `datoms/NNN.kotoba.edn` | the same corpus as kotoba EAVT |
| `publish-manifest.edn` | per-shard bytes + CIDv1 + item counts |
| `ingest-provenance.edn` | source-by-source status, including what has not run |
| `dataset.edn` | DataLad dataset descriptor |

`corpus/` and `datoms/` are **derived** from the journal and rebuildable:

```bash
# from a cloud-itonami/hirameki checkout
clojure -M -m hirameki.methods.dataset --dataset ../hirameki-patents --as-of 2026-08-10
```

## Verify

Two gates, because they check different claims.

```bash
clojure -M verify.clj          # the bytes are what the manifest says
clojure -M:query query-check.clj   # the corpus actually answers questions
```

`verify.clj` re-derives every shard's CIDv1/raw/sha2-256 from the bytes on disk.
No daemon, no network. It also checks that the shards' item counts add up — a
CID proves a shard is intact, never that the set of shards is complete. Details
and the reason the artifacts are sharded at all are in [`PUBLISH.md`](PUBLISH.md).

`query-check.clj` transacts every `datoms/` shard into DataScript and runs real
queries — count by holder, roll up by jurisdiction, join a holder to its
patents, compare the release clock numerically — and asserts the published
artifact carries no verdict, no `imposes`, and no inventor attribute (G1/G2/G6
hold in the ARTIFACT, not only in the code that wrote it). Hashing perfectly and
being queryable are different claims; this checks the second.

Confirmed both directions: renaming the assignee attribute across all shards
exits 1, and so does introducing an inventor attribute.

## Custody — where this actually lives, measured

**One durable copy.** That is the honest state, and it is the largest gap in
this dataset.

| store | state (measured 2026-08-10) |
|---|---|
| GitHub `cloud-itonami/hirameki-patents` | **the corpus, in git, as EDN** — real, and the only durable copy |
| local checkouts | 2, both on one operator machine |
| git-annex | **not initialized in this repo.** 0 files annexed, no content remote |
| IPFS | CIDs computed; **nothing pinned.** No gateway can serve them |
| Radicle (`rad:z3yMT2MUPS4PwTekwt3wboCAyRxm1`) | id registered; **no replica on this node** |

### About the DataLad claim

An earlier version of this file said "this is a real DataLad dataset,
git-annex initialized — as of 2026-08-10 it is one, rather than only claiming to
be." **That was wrong.** `datalad create` was run in a throwaway clone, and the
annex it initialized lived in that clone's `.git/config`, which is local-only and
was never pushed. What is COMMITTED is the declaration — `.datalad/config` and
the `.gitattributes` routing rules — not the substrate. Clone this repo and you
get a plain git repository with a `.datalad/` directory in it.

The routing rules remain correct and useful: when a bulk operator pull arrives
(`*.tsv`, `*.raw.edn`), it is meant to go to annex rather than git. But `git
annex init` has not been run here, the `git-annex` branch does not exist on the
remote, and no special remote is configured.

### About the CIDs

They are **verifiable, not fetchable**. `clojure -M verify.clj` re-derives every
shard's CIDv1 from bytes you already hold, with no daemon and no network — that
works and is checked. But nothing has been `ipfs add`ed for real, so fetching
`https://ipfs.io/ipfs/<cid>` returns nothing. Measured: ipfs.io timed out,
dweb.link redirected into a subdomain gateway that has no such block.

### What would close this

Not annex, at this size — **replication**. The corpus is 780 KB of EDN and git
handles it perfectly; what is missing is a second independent custodian. The
`large-binary-datalad` convention asks for `numcopies`, independent remotes,
periodic `fsck` and a recovery drill; this dataset currently satisfies none of
them.

## Scope

Bibliographic metadata only: title, number, jurisdiction, filing/grant date,
applicant organizations, cited patents. Never claims, never specification text,
never a paywall or bot-detection bypass, never a natural person.

## License

Apache-2.0. The underlying bibliographic facts are public records.
