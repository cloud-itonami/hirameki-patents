#!/usr/bin/env python3
"""Read verified patent bytes through existing SSH to either localhost gateway.
No exposed API, anonymous admin access, or unverified fallback is introduced.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
from epo_node import cid, LIMIT, atomic
from epo_publish import ssh


def fetch(nodes, identity, expected_sha256, expected_size):
    if not re.fullmatch(r'bafkrei[a-z2-7]{52}', identity) or not re.fullmatch(r'[0-9a-f]{64}', expected_sha256):
        raise ValueError('invalid expected patent identity or hash')
    if not isinstance(expected_size, int) or not 0 < expected_size <= LIMIT:
        raise ValueError('invalid expected patent size')
    failed = []
    for node in nodes:
        try:
            data = ssh(node, ['curl', '--fail', '--silent', '--show-error', '--max-time', '15',
                '--max-filesize', str(LIMIT), 'http://127.0.0.1:8083/ipfs/' + identity], timeout=25)
            if len(data) != expected_size or hashlib.sha256(data).hexdigest() != expected_sha256 or cid(data) != identity:
                raise ValueError('peer bytes differ from expected patent manifest')
            return data, {'status': 'verified-peer-read', 'node': node['name'], 'cid': identity,
                'sha256': expected_sha256, 'bytes': len(data), 'failedPeers': failed}
        except (RuntimeError, ValueError, OSError, subprocess.TimeoutExpired):
            failed.append(node['name'])
    raise RuntimeError('all patent peers unavailable or failed integrity verification')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--nodes', required=True)
    p.add_argument('--cid', required=True)
    p.add_argument('--sha256', required=True)
    p.add_argument('--bytes', type=int, required=True)
    p.add_argument('--output', required=True)
    args = p.parse_args()
    data, receipt = fetch(json.loads(Path(args.nodes).read_text()), args.cid, args.sha256, args.bytes)
    atomic(Path(args.output), data)
    print(json.dumps(receipt))
