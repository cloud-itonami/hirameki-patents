# Public EPO observations and distributed custody

This collection belongs in `cloud-itonami/hirameki-patents`, the existing public
patent dataset. `epo/hyakka-pilot-20261013.json` preserves the 11 publications and
98 sourced claims published by Hyakka, byte for byte. The SHA-256 proof is adjacent.
These are historical bibliographic observations under CC BY 4.0, attributed to
the European Patent Office. No inventor/person data or legal-validity conclusions
are collected. EP-only backfill is not worldwide or current-event completeness.

Two independent collectors on Jacob and Xavier fetch one ten-record EPO page
every six hours. They keep independent checkpoints. A checkpoint advances only
after local IPFS pin and exact readback. A fetch/parser/pin failure exits nonzero
and records failed health. It preserves the previous checkpoint and published data.
Overlapping observations are intentionally retained with provenance; publication
identity is `EP-number-kind`, and consumers must deduplicate by that identity.

Each immutable JSON shard is bounded to 256 KiB, identified by SHA-256 and a real
CIDv1/raw/sha2-256. The GitHub projector fetches both node inventories, rejects
stale receipts, reads every shard, pins and reads it back on BOTH nodes, creates
an immutable content-derived Release, downloads it, and checks every byte again.
It never overwrites release assets or deletes previous releases/pins. A missing
custodian refuses promotion and leaves the previous release available.

Git contains small bibliographic data and manifests. Growing snapshots use
GitHub Releases with small assets, rather than accumulating large binary history
or using paid Git LFS. Immutable assets are stored once per monthly shard release;
snapshot releases hold manifests that reference those assets. Node inventories
rotate monthly while retaining and pinning the previous inventory. Each epoch
is limited to 900 shards. GitHub is a public storage/projection
and read path; collection does not use GitHub Actions.

Runtime entry points:

```
python3 -m unittest discover -s test -p test_epo_node.py
python3 scripts/install_epo_nodes.py --nodes <private-node-inventory>
python3 scripts/epo_publish.py --nodes <private-node-inventory> --state <scratch-state> --commit <merged-full-SHA>
```

The GitHub projector uses the operator Mac's existing `gh` authentication.
Credentials are not sent to either collector. This is a remaining publication
dependency: collector and IPFS storage survive loss of the Mac, but new GitHub
Releases wait until its projector resumes. Two collectors are not distributed
consensus, and IPFS pins alone do not establish public-gateway availability.
The public Hyakka Worker currently remains the separate initial pilot view.
See `live-custody-20261013.json` for measured receipts, not a configuration claim.
