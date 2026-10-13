#!/usr/bin/env python3
"""Project verified two-node EPO observations to immutable public GitHub Releases.
No Actions, private corpus, remote credentials or destructive retention.
"""
import argparse
import datetime as dt
import fcntl
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import tempfile
from epo_node import atomic, canonical, cid, LIMIT

REPO = 'cloud-itonami/hirameki-patents'
ROOT = Path(__file__).resolve().parents[1]


def run(argv, **kw):
    r = subprocess.run(argv, capture_output=True, timeout=kw.pop('timeout', 120), **kw)
    if r.returncode:
        raise RuntimeError(f'{argv[0]} failed: ' + r.stderr.decode(errors='replace')[:200])
    return r.stdout


def ssh(node, argv, **kw):
    return run(['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', node['ssh'], shlex.join(argv)], **kw)


def validate(data, row):
    if len(data) != row['bytes'] or len(data) > LIMIT or cid(data) != row['cid'] or hashlib.sha256(data).hexdigest() != row['sha256']:
        raise ValueError('shard custody hash differs')
    obj = json.loads(data)
    if obj.get('schema') != 'epo-bibliography.v1' or not obj.get('observations') or obj.get('complete') is not False:
        raise ValueError('invalid patent shard schema')
    for observation in obj['observations']:
        p = observation['publication']
        if set(p) != {'id', 'authority', 'title', 'publicationDate', 'applicationNumber', 'ipc'} or p['authority'] != 'EP':
            raise ValueError('unscoped patent publication')
        prov = observation['provenance']
        if not prov['url'].startswith('https://data.epo.org/linked-data/data/publication/EP.json?') or prov['license'] != 'CC BY 4.0':
            raise ValueError('unapproved source/license')
    return obj


def publish(args):
    state = Path(args.state)
    state.mkdir(parents=True, exist_ok=True)
    with (state / 'publish.lock').open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        nodes = json.loads(Path(args.nodes).read_text())
        if len(nodes) != 2 or len({n['name'] for n in nodes}) != 2:
            raise ValueError('two independent custodians required')
        gathered, inventory, nodes_status = {}, {}, []
        for node in nodes:
            current = json.loads(ssh(node, ['cat', node['root'] + '/state/current.json']))
            when = dt.datetime.fromisoformat(current['collectedAt'])
            if current['node'] != node['name'] or (dt.datetime.now(dt.timezone.utc) - when).total_seconds() > 90000:
                raise ValueError('stale or wrong-node collection receipt')
            for row in current['shards']:
                if row['cid'] not in gathered:
                    data = ssh(node, ['cat', node['root'] + '/state/objects/' + row['cid'] + '.json'])
                    validate(data, row)
                    gathered[row['cid']] = data
                    inventory[row['cid']] = row
            nodes_status.append({'node': node['name'], 'collectedAt': current['collectedAt'], 'nextPage': current['nextPage']})
        if not gathered or len(gathered) > 900:
            raise ValueError('empty or oversized release; rotate release epoch')
        receipts = []
        with tempfile.TemporaryDirectory(dir=state) as tmp:
            directory = Path(tmp)
            for identity, data in sorted(gathered.items()):
                path = directory / (identity + '.json')
                path.write_bytes(data)
                for node in nodes:
                    target = node['root'] + '/incoming.json'
                    run(['scp', '-q', str(path), node['ssh'] + ':' + target])
                    r = json.loads(ssh(node, [node['python'], node['root'] + '/epo_node.py', 'pin',
                        '--file', target, '--node', node['name'], '--state', node['root'] + '/state',
                        '--ipfs-bin', node['ipfsBin'], '--ipfs-path', node['ipfsPath'], '--api', node['api']]))
                    if r['cid'] != identity or r['status'] != 'pinned-and-readback':
                        raise ValueError('replica receipt differs')
                    receipts.append(r)
            manifest = {'schema': 'epo-release.v1', 'complete': False, 'authorities': ['EP'],
                'license': 'CC BY 4.0', 'attribution': 'European Patent Office',
                'nodes': nodes_status, 'shards': [inventory[k] for k in sorted(inventory)],
                'replicaReceipts': receipts}
            body = canonical(manifest)
            path = directory / 'manifest.json'
            path.write_bytes(body)
            tag = 'epo-' + hashlib.sha256(body).hexdigest()[:24]
            found = subprocess.run(['gh', 'release', 'view', tag, '--repo', REPO], capture_output=True, timeout=45)
            if found.returncode:
                run(['gh', 'release', 'create', tag, '--repo', REPO, '--target', args.commit,
                    '--title', 'EPO public bibliographic observations ' + tag,
                    '--notes', 'Bounded EP backfill, not worldwide completeness. CC BY 4.0 European Patent Office. Inventor/person and legal-validity fields excluded. Every shard is raw-CID verified on Jacob and Xavier.',
                    '--latest=false', *map(str, sorted(directory.glob('*.json')))], timeout=300)
            restore = directory / 'restore'
            restore.mkdir()
            run(['gh', 'release', 'download', tag, '--repo', REPO, '--dir', str(restore)], timeout=300)
            if (restore / 'manifest.json').read_bytes() != body:
                raise ValueError('GitHub manifest readback differs')
            for identity in gathered:
                validate((restore / (identity + '.json')).read_bytes(), inventory[identity])
            result = {'status': 'published-and-restored', 'at': dt.datetime.now(dt.timezone.utc).isoformat(),
                'release': f'https://github.com/{REPO}/releases/tag/{tag}', 'manifestSha256': hashlib.sha256(body).hexdigest(),
                'shards': len(gathered), 'replicas': [n['name'] for n in nodes], 'manifest': manifest}
            atomic(state / 'last-success.json', canonical(result))
            atomic(state / 'health.json', canonical({'status': 'ok', 'at': result['at'], 'release': result['release']}))
            print(json.dumps({k: v for k, v in result.items() if k != 'manifest'}))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--state', required=True)
    p.add_argument('--commit', required=True)
    p.add_argument('--nodes', default=str(ROOT / 'epo/nodes.json'))
    args = p.parse_args()
    try:
        publish(args)
    except Exception as e:
        atomic(Path(args.state) / 'health.json', canonical({'status': 'failed', 'at': dt.datetime.now(dt.timezone.utc).isoformat(), 'error': str(e)[:300]}))
        raise


if __name__ == '__main__':
    main()
