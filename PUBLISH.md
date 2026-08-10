# hirameki 閃き — published public-patent corpus

> PUBLIC patent bibliographic data only — aggregate-first, no person-level inventor (G6) ·
> ADR-2606212200 · a RELEASE map, never an FTO/infringement verdict (G1)

The corpus, content-addressed to IPFS CIDv1 (raw, sha2-256, base32). Every shard's
CID is byte-identical to `ipfs add --cid-version=1 --raw-leaves` and checkable
with **no daemon and no network**.

## The CIDs live in `publish-manifest.edn`, not here

They are not repeated in this file on purpose. A table of hashes in prose goes
stale the first time the corpus grows, and a stale hash beside a live file is
worse than no hash at all. Read the manifest:

```bash
clojure -M:query verify.clj        # re-derives every CID from the bytes on disk
```

It checks four things, and fails with exit 1 on any of them:

1. each shard's byte count matches the manifest
2. each shard's CIDv1/raw matches the manifest
3. **no shard is at or past 256 KiB** (see below)
4. **the item counts add up** — every shard can be internally perfect while the
   set of shards is short one

## Why the corpus is sharded

`bafkrei…` is the hash of ONE raw block. It equals what `ipfs add` produces only
while a file stays under the 256 KiB chunker limit; past that IPFS builds a
UnixFS DAG whose root is a `bafybei…` dag-pb CID. Measured 2026-08-10, when the
corpus went from 7 rows to 625:

```
corpus 280,078 bytes
  raw-block CID  bafkreibo345qp6u5zkpf3zrbp4hbwtl6u5ov53gsixb43azzgnw7svk3va
  ipfs add       bafybeicpvod7rmqy2l74m32tjf3gtaez6q2axx5pznwofi4aaeedlcy3pm
```

The published CID had quietly become unverifiable. Rather than take on a UnixFS
DAG builder — which would make publishing depend on an IPFS implementation and
defeat the "verify without a daemon" promise — rows are packed into shards that
stay inside one block. `write!` refuses to publish an over-limit shard.

## The CIDs are verifiable, not fetchable

```bash
clojure -M:query verify.clj    # re-derives every CID from the bytes on disk
```

That works, needs no daemon and no network, and is checked in both directions.

**What does NOT work today: fetching by CID.** Nothing here has been `ipfs
add`ed for real — the CIDs are computed, not published. Measured 2026-08-10:
`https://ipfs.io/ipfs/<cid>` times out and `https://dweb.link/ipfs/<cid>`
redirects to a subdomain gateway with no such block. An earlier version of this
file printed a `curl` from those gateways as if it would return the corpus. It
would not.

So the CID means: *if you obtain these bytes by any route, you can prove they
are the bytes this manifest names.* It does not yet mean: *you can obtain them
from IPFS.* Closing that needs a real pin, which needs a node or a pinning
service; see the custody section of the README.

## Layout

| path | what |
|---|---|
| `80-data/public/google-patents.NNNN.journal.edn` | the raw harvest journal — append-only `[e a v tx op]` quads, git-authoritative (ADR-2607072300) |
| `corpus/NNN.kotoba.edn` | normalized patent rows, sorted by id, sharded |
| `datoms/NNN.kotoba.edn` | the same corpus as kotoba EAVT, sharded |
| `publish-manifest.edn` | per-shard bytes + CID + item counts |
| `ingest-provenance.edn` | where the rows came from, and which sources have not run |

The journal is the input; `corpus/` and `datoms/` are derived from it and can be
rebuilt at any time:

```bash
clojure -M -m hirameki.methods.dataset --dataset <this repo> --as-of <date>   # in cloud-itonami/hirameki
```

---
_Published by the [hirameki](https://github.com/cloud-itonami/hirameki) actor.
The bulk legs (USPTO ODP / EPO OPS / WIPO) are operator steps and have not run;
`ingest-provenance.edn` says so per source rather than implying coverage._
