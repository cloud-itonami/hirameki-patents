#!/usr/bin/env python3
"""Independent bounded EPO collector and verified raw-CID custodian. No secrets."""
import argparse
import base64
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

LIMIT = 262144
BASE = 'https://data.epo.org/linked-data/data/publication/EP.json'


def canonical(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()


def cid(data):
    return 'b' + base64.b32encode(bytes([1, 0x55, 0x12, 0x20]) + hashlib.sha256(data).digest()).decode().lower().rstrip('=')


def atomic(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(f.name, path)


def parse(payload, source, fetched):
    rows = payload.get('result', {}).get('items')
    if payload.get('format') != 'linked-data-api' or not isinstance(rows, list) or not rows:
        raise ValueError('empty or malformed EPO page')
    output = []
    digest = hashlib.sha256(canonical(payload)).hexdigest()
    for row in rows:
        match = re.fullmatch(r'https?://data\.epo\.org/linked-data/data/publication/(EP)/(\d+)/([A-Z]\d+)/-', row.get('_about', ''))
        if not match:
            raise ValueError('not an official EP identity')
        office, number, kind = match.groups()
        authority = row.get('publicationAuthority')
        if isinstance(authority, dict):
            authority = authority.get('_about')
        if authority != 'http://data.epo.org/linked-data/id/st3/EP' or row.get('label') != f'{office} {number} {kind}' or row.get('publicationKind', {}).get('label') != kind:
            raise ValueError('contradictory EP identity')
        titles = row.get('titleOfInvention', [])
        if isinstance(titles, str):
            titles = [titles]
        application = row.get('application', {})
        application_number = application.get('applicationNumber') if isinstance(application, dict) else None
        if isinstance(application, str):
            application_match = re.fullmatch(r'http://data\.epo\.org/linked-data/id/application/EP/(\d+)', application)
            application_number = application_match.group(1) if application_match else None
        ipc = row.get('classificationIPCInventive', [])
        if isinstance(ipc, dict):
            ipc = [ipc]
        values = {'id': f'{office}-{number}-{kind}', 'authority': office,
                  'title': [v for v in titles if isinstance(v, str)],
                  'publicationDate': row.get('publicationDate'),
                  'applicationNumber': application_number,
                  'ipc': [v['label'] for v in ipc if isinstance(v, dict) and isinstance(v.get('label'), str)]}
        if not values['title']:
            raise ValueError('publication without title')
        output.append({'publication': values, 'provenance': {'url': source, 'retrievedAt': fetched,
                        'sourceCanonicalSha256': digest, 'license': 'CC BY 4.0', 'attribution': 'European Patent Office'}})
    return output


def ipfs(args, *command):
    env = dict(os.environ, IPFS_PATH=args.ipfs_path)
    return subprocess.check_output([args.ipfs_bin, '--api', args.api, *command], env=env, timeout=90)


def store(args, data):
    if not data or len(data) > LIMIT:
        raise ValueError('empty or oversized shard')
    expected = cid(data)
    path = Path(args.state) / 'objects' / (expected + '.json')
    atomic(path, data)
    actual = ipfs(args, 'add', '-Q', '--cid-version=1', '--raw-leaves', '--chunker=size-262144', '--pin=true', str(path)).decode().strip()
    if actual != expected or ipfs(args, 'cat', expected) != data:
        raise ValueError('IPFS custody readback differs')
    return {'cid': expected, 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}


def collect(args):
    state = Path(args.state)
    state.mkdir(parents=True, exist_ok=True)
    with (state / 'lock').open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        previous = json.loads((state / 'current.json').read_text()) if (state / 'current.json').exists() else {'nextPage': 0, 'shards': []}
        page = previous['nextPage']
        url = BASE + f'?_pageSize=10&_view=all&_page={page}'
        now = dt.datetime.now(dt.timezone.utc).isoformat()
        # Overall wall-clock deadline includes DNS/TLS and slow response bodies.
        raw = subprocess.check_output(['curl', '--fail', '--silent', '--show-error',
            '--connect-timeout', '10', '--max-time', '45', '--max-filesize', '2097152', url], timeout=55)
        if len(raw) > 2 * 1024 * 1024:
            raise ValueError('oversized EPO response')
        payload = json.loads(raw)
        observations = parse(payload, url, now)
        data = canonical({'schema': 'epo-bibliography.v1', 'complete': False, 'observations': observations})
        shard = store(args, data)
        shard.update({'records': len(observations), 'page': page, 'source': url, 'retrievedAt': now})
        shards = previous['shards']
        if previous.get('epoch') and previous['epoch'] != now[:7]:
            archive = canonical(previous)
            store(args, archive)
            atomic(state / 'inventories' / (previous['epoch'] + '.json'), archive)
            shards = []
        result = {'schema': 'epo-node.v1', 'node': args.node, 'collectedAt': now,
                  'nextPage': page + 1 if payload['result'].get('next') else 0,
                  'complete': False, 'epoch': now[:7], 'shards': shards + [shard]}
        atomic(state / 'current.json', canonical(result))
        atomic(state / 'health.json', canonical({'status': 'ok', 'node': args.node, 'at': now, 'lastShard': shard}))
        print(json.dumps({'status': 'collected-and-pinned', 'node': args.node, **shard}))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=['collect', 'pin'])
    p.add_argument('--state', required=True)
    p.add_argument('--node', required=True)
    p.add_argument('--ipfs-bin', required=True)
    p.add_argument('--ipfs-path', required=True)
    p.add_argument('--api', required=True)
    p.add_argument('--file')
    args = p.parse_args()
    try:
        if args.command == 'collect':
            collect(args)
        else:
            data = Path(args.file).read_bytes()
            obj = json.loads(data)
            if not isinstance(obj, dict):
                raise ValueError('expected JSON patent object')
            print(json.dumps({'status': 'pinned-and-readback', 'node': args.node, **store(args, data)}))
    except Exception as error:
        if args.command == 'collect':
            atomic(Path(args.state) / 'health.json', canonical({'status': 'failed', 'node': args.node,
                'at': dt.datetime.now(dt.timezone.utc).isoformat(), 'error': str(error)[:300]}))
        raise


if __name__ == '__main__':
    main()
