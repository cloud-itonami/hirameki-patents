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
| patents | **625** (618 harvested + 7 curated) |
| citation edges | 2,448 |
| distinct cited ids | 1,945 — of which **1,331 are still unharvested frontier** |
| jurisdictions | 20 (US 347, JP 145, EP 49, WO 39, GB 24, …) |
| named assignees | 287 · named-HHI **0.013** |
| CPC classification | **absent** — see below |

**This is a citation-graph neighbourhood, not a sample.** It was grown by walking
outward from four seed patents (CRISPR-Cas9 ×2, an aqueous coating composition,
mRNA-LNP), so its shape reflects those seeds: Kansai Paint is the top assignee at
7.4% because one seed was a paint patent, not because coatings dominate the
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
| `80-data/public/google-patents.journal.edn` | the harvest journal — append-only `[e a v tx op]` quads. **The input, and the authoritative record** (ADR-2607072300) |
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

## DataLad

This is a real DataLad dataset (`datalad create`, git-annex initialized) — as of
2026-08-10 it is one, rather than only claiming to be.

**Nothing is annexed, and that is a decision rather than an omission.**

The journal is sharded at 1 MiB and a sealed shard never changes again, so git
stores each exactly once — the growth is linear in facts, not quadratic in
commits. At that size annexing would cost `git diff` and `git blame` on the
artifact ADR-2607072300 designates as authoritative, and buy nothing.

The annex is for what git is genuinely bad at: the bulk operator pulls
(`*.tsv`, `*.tsv.zip`, `*.raw.edn`) that USPTO ODP / EPO OPS produce as single
multi-gigabyte files with no useful line structure. **When the first one lands,
it will need a content remote** (B2 or IPFS, per the workspace's
`large-binary-datalad` convention) — one is not configured now because there is
nothing to put in it, and GitHub cannot serve annexed content in any case
(`git-annex-shell` is not available there).

## Scope

Bibliographic metadata only: title, number, jurisdiction, filing/grant date,
applicant organizations, cited patents. Never claims, never specification text,
never a paywall or bot-detection bypass, never a natural person.

## License

Apache-2.0. The underlying bibliographic facts are public records.
