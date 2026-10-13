#!/usr/bin/env python3
"""Install only the patent collector on existing Kubo hosts; preserve other jobs."""
import json
import argparse
from pathlib import Path
import plistlib
import shlex
import subprocess
from epo_publish import ROOT, run, ssh


def install(node):
    root = node['root']
    ssh(node, ['mkdir', '-p', root + '/state', root + '/logs'])
    run(['scp', '-q', str(ROOT / 'scripts/epo_node.py'), node['ssh'] + ':' + root + '/epo_node.py'])
    argv = [node['python'], root + '/epo_node.py', 'collect', '--node', node['name'], '--state', root + '/state',
            '--ipfs-bin', node['ipfsBin'], '--ipfs-path', node['ipfsPath'], '--api', node['api']]
    if ssh(node, ['uname', '-s']).decode().strip() == 'Darwin':
        label = 'com.cloud-itonami.epo-collector'
        body = plistlib.dumps({'Label': label, 'ProgramArguments': argv,
            'WorkingDirectory': root, 'StartInterval': 21600, 'RunAtLoad': False,
            'StandardOutPath': root + '/logs/out.log', 'StandardErrorPath': root + '/logs/err.log'})
        home = ssh(node, [node['python'], '-c', 'from pathlib import Path; print(Path.home())']).decode().strip()
        path = home + '/Library/LaunchAgents/' + label + '.plist'
        ssh(node, ['tee', path], input=body)
        uid = ssh(node, ['id', '-u']).decode().strip()
        loaded = ssh(node, ['launchctl', 'print', 'gui/' + uid + '/' + label])
        if label.encode() not in loaded:
            ssh(node, ['launchctl', 'bootstrap', 'gui/' + uid, path])
    else:
        service = '[Unit]\nDescription=Bounded public EPO collector and IPFS custodian\nAfter=network-online.target\n[Service]\nType=oneshot\nExecStart=' + shlex.join(argv) + '\nWorkingDirectory=' + root + '\n'
        timer = '[Unit]\nDescription=Independent six-hour EPO collection\n[Timer]\nOnBootSec=10min\nOnUnitActiveSec=6h\nPersistent=true\n[Install]\nWantedBy=timers.target\n'
        ssh(node, ['tee', '/etc/systemd/system/epo-collector.service'], input=service.encode())
        ssh(node, ['tee', '/etc/systemd/system/epo-collector.timer'], input=timer.encode())
        ssh(node, ['systemctl', 'daemon-reload'])
        ssh(node, ['systemctl', 'enable', '--now', 'epo-collector.timer'])
    result = json.loads(ssh(node, argv, timeout=180))
    if result.get('status') != 'collected-and-pinned' or result.get('node') != node['name']:
        raise ValueError('collector did not return a positive node-specific receipt')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--nodes', required=True, help='private operator node inventory')
    args = parser.parse_args()
    for node in json.loads(Path(args.nodes).read_text()):
        install(node)
