# hirameki 閃き — published public-patent corpus

> PUBLIC patent bibliographic data only — aggregate-first, no person-level inventor (G6) ·
> ADR-2606212200 (supersedes 2604251024) · a RELEASE map, never an FTO/infringement verdict (G1)

The patent corpus, content-addressed to kotoba IPFS (CIDv1, raw, sha2-256). The CID is
byte-identical to `ipfs add --cid-version=1 --raw-leaves` and verifiable with
`bb verify` — no daemon required.

## Artifacts

| artifact | file | bytes | CID |
|---|---|---:|---|
| corpus (EDN) | `hirameki-patents.corpus.kotoba.edn` | 2055 | `bafkreiacmpjkhjncxlfjtfhfia7ikjyfjq42u7yi3x56ajppu374t3j4gi` |
| datoms (EAVT) | `hirameki-patents.datoms.kotoba.edn` | 6255 | `bafkreif7ricl4x24y5pnquryjf4gakmwm36uqijtsao3rw2cuxuwflw4be` |

(Both verified byte-identical against `ipfs add --cid-version=1 --raw-leaves` 2026-06-21.)

## Fetch + verify (trustless, no daemon trust)

```bash
curl -sSL https://ipfs.io/ipfs/bafkreiacmpjkhjncxlfjtfhfia7ikjyfjq42u7yi3x56ajppu374t3j4gi -o corpus.edn
ipfs add -Q --cid-version=1 --raw-leaves --only-hash corpus.edn   # compare to the CID above
```

Gateways: https://ipfs.io/ipfs/, https://dweb.link/ipfs/, https://cloudflare-ipfs.com/ipfs/

---
_Published by the hirameki actor under G9. The full-world ~200M-patent corpus goes via DataLad→IPFS (git-annex);
this bounded R0 snapshot is git-tracked directly (no git-lfs, G8)._
