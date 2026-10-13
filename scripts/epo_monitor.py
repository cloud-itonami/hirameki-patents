#!/usr/bin/env python3
"""Check current projector health, two-node collection freshness and public bytes."""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import subprocess
from epo_publish import ssh, validate, REPO
from epo_node import atomic, canonical


def check(state, nodes):
    health = json.loads((state / 'health.json').read_text())
    if health.get('status') != 'ok':
        raise ValueError('latest projection failed')
    if (dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(health['at'])).total_seconds() > 28800:
        raise ValueError('projector heartbeat older than eight hours')
    success = json.loads((state / 'last-success.json').read_text())
    for node in nodes:
        current = json.loads(ssh(node, ['cat', node['root'] + '/state/health.json']))
        if current.get('status') != 'ok' or current.get('node') != node['name']:
            raise ValueError('node collection failed')
        if (dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(current['at'])).total_seconds() > 25200:
            raise ValueError('node collection older than seven hours')
        if node.get('api') != 'offline':
            if node.get('api') != '/ip4/127.0.0.1/tcp/5003':
                raise ValueError('unexpected patent Kubo API scope')
            identity = json.loads(ssh(node, ['curl', '-fsS', '--max-time', '10', '-X', 'POST',
                'http://127.0.0.1:5003/api/v0/id']))
            if identity.get('ID') != node.get('peerId'):
                raise ValueError('patent Kubo identity differs')
            listeners = json.loads(ssh(node, ['curl', '-fsS', '--max-time', '10', '-X', 'POST',
                'http://127.0.0.1:5003/api/v0/swarm/addrs/listen']))
            if listeners.get('Strings') != ['/ip4/' + node['ssh'].rsplit('@',1)[-1] + '/tcp/4003']:
                raise ValueError('patent Swarm listener scope differs')
            peers = json.loads(ssh(node, ['curl', '-fsS', '--max-time', '10', '-X', 'POST',
                'http://127.0.0.1:5003/api/v0/swarm/peers']))
            expected = {n['peerId'] for n in nodes if n['name'] != node['name']}
            if not expected.issubset({p['Peer'] for p in peers.get('Peers',[])}):
                raise ValueError('patent direct peer disconnected')
    tag = success['release'].rsplit('/', 1)[-1]
    def public_bytes(url):
        return subprocess.check_output(['curl', '--fail', '--silent', '--show-error', '--location',
            '--connect-timeout', '10', '--max-time', '45', '--max-filesize', '2097152', url], timeout=55)
    body = public_bytes(f'https://github.com/{REPO}/releases/download/{tag}/manifest.json')
    if hashlib.sha256(body).hexdigest() != success['manifestSha256']:
        raise ValueError('public manifest hash differs')
    manifest = json.loads(body)
    if len({r['node'] for r in manifest['replicaReceipts']}) != 2 or not manifest['shards']:
        raise ValueError('public manifest lacks two-custodian evidence')
    row = manifest['shards'][-1]
    data = public_bytes(f"https://github.com/{REPO}/releases/download/{row['assetRelease']}/{row['cid']}.json")
    validate(data, row)
    return {'status': 'ok', 'publicRelease': success['release'], 'shards': len(manifest['shards']), 'custodians': 2}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--state', required=True)
    p.add_argument('--nodes', required=True)
    args = p.parse_args()
    state = Path(args.state)
    try:
        result = check(state, json.loads(Path(args.nodes).read_text()))
        result['at'] = dt.datetime.now(dt.timezone.utc).isoformat()
        atomic(state / 'monitor-health.json', canonical(result))
        print(json.dumps(result))
    except Exception as error:
        atomic(state / 'monitor-health.json', canonical({'status': 'failed',
            'at': dt.datetime.now(dt.timezone.utc).isoformat(), 'error': str(error)[:300]}))
        raise
