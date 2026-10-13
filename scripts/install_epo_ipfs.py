#!/usr/bin/env python3
"""Install explicitly approved patent-only Kubo, on Tailnet TCP 4003 only.
Admin API/gateway bind localhost. Existing Kubo instances are never restarted.
Private node inventories, custody keys/config backups never enter this repo.
"""
import argparse
import ipaddress
import json
from pathlib import Path
import plistlib
import shlex
import time
from epo_publish import ssh


def tailnet_host(node):
    address = node['ssh'].rsplit('@', 1)[-1]
    if ipaddress.ip_address(address) not in ipaddress.ip_network('100.64.0.0/10'):
        raise ValueError('patent Swarm must bind an explicit Tailnet IPv4 address')
    return address


def install(nodes):
    if len(nodes) != 2 or len({tailnet_host(n) for n in nodes}) != 2:
        raise ValueError('two distinct Tailnet hosts required')
    for node in nodes:
        env = ['env', 'IPFS_PATH=' + node['ipfsPath'], node['ipfsBin']]
        node['peerId'] = ssh(node, env + ['--offline', 'config', 'Identity.PeerID']).decode().strip()
        if not node['peerId'].startswith('12D3KooW'):
            raise ValueError('missing existing patent custody peer identity')
    for node in nodes:
        host = tailnet_host(node)
        env = ['env', 'IPFS_PATH=' + node['ipfsPath'], node['ipfsBin']]
        # Backup stays in the existing private custody directory, never exported.
        backup = 'from pathlib import Path; import shutil,datetime; p=Path(' + repr(node['ipfsPath']) + '); shutil.copy2(p/"config",p/("config.before-tailnet-"+datetime.datetime.now().strftime("%Y%m%dT%H%M%S")))'
        ssh(node, [node['python'], '-c', backup])
        settings = {
            'Addresses.API': '/ip4/127.0.0.1/tcp/5003',
            'Addresses.Gateway': '/ip4/127.0.0.1/tcp/8083',
            'Addresses.Swarm': [f'/ip4/{host}/tcp/4003'],
            'Addresses.Announce': [f'/ip4/{host}/tcp/4003'],
            'Bootstrap': [], 'Routing.Type': 'none', 'Provide.Enabled': False,
            'Discovery.MDNS.Enabled': False,
            'AutoTLS.Enabled': False,
            'Swarm.Transports.Network.TCP': True,
            'Swarm.Transports.Network.Websocket': False,
            'Swarm.Transports.Network.QUIC': False,
            'Swarm.Transports.Network.Relay': False,
            'Swarm.Transports.Network.WebTransport': False,
            'Swarm.Transports.Network.WebRTCDirect': False,
            'Peering.Peers': [{'ID': other['peerId'], 'Addrs': [f'/ip4/{tailnet_host(other)}/tcp/4003']}
                             for other in nodes if other['name'] != node['name']],
        }
        for key, value in settings.items():
            ssh(node, env + ['config', '--json', key, json.dumps(value)])
        argv = [node['ipfsBin'], 'daemon']
        if ssh(node, ['uname', '-s']).decode().strip() == 'Darwin':
            label = 'com.cloud-itonami.patent-ipfs'
            home = ssh(node, [node['python'], '-c', 'from pathlib import Path; print(Path.home())']).decode().strip()
            path = home + '/Library/LaunchAgents/' + label + '.plist'
            body = plistlib.dumps({'Label': label, 'ProgramArguments': argv,
                'EnvironmentVariables': {'IPFS_PATH': node['ipfsPath']},
                'WorkingDirectory': node['root'], 'RunAtLoad': True, 'KeepAlive': True,
                'StandardOutPath': node['root'] + '/logs/ipfs-out.log',
                'StandardErrorPath': node['root'] + '/logs/ipfs-err.log'})
            # This is a first-install operation: do not replace unknown definitions.
            probe = ssh(node, [node['python'], '-c', 'from pathlib import Path; print(Path(' + repr(path) + ').exists())']).decode().strip()
            if probe != 'False':
                raise ValueError('patent Kubo launchd definition already exists; reconcile explicitly')
            ssh(node, ['tee', path], input=body)
            uid = ssh(node, ['id', '-u']).decode().strip()
            ssh(node, ['launchctl', 'bootstrap', 'gui/' + uid, path])
        else:
            path = '/etc/systemd/system/patent-ipfs.service'
            probe = ssh(node, [node['python'], '-c', 'from pathlib import Path; print(Path(' + repr(path) + ').exists())']).decode().strip()
            if probe != 'False':
                raise ValueError('patent Kubo systemd definition already exists; reconcile explicitly')
            body = '[Unit]\nDescription=Patent-only Tailnet IPFS custody\nAfter=network-online.target\nWants=network-online.target\n[Service]\nEnvironment=IPFS_PATH=' + node['ipfsPath'] + '\nExecStart=' + shlex.join(argv) + '\nWorkingDirectory=' + node['root'] + '\nRestart=on-failure\nRestartSec=5\n[Install]\nWantedBy=multi-user.target\n'
            ssh(node, ['tee', path], input=body.encode())
            ssh(node, ['systemctl', 'daemon-reload'])
            ssh(node, ['systemctl', 'enable', '--now', 'patent-ipfs.service'])
        node['api'] = '/ip4/127.0.0.1/tcp/5003'
        deadline = time.monotonic() + 45
        while True:
            try:
                result = json.loads(ssh(node, ['curl', '-fsS', '--max-time', '3', '-X', 'POST', 'http://127.0.0.1:5003/api/v0/id']))
                if result['ID'] != node['peerId']:
                    raise ValueError('Kubo API belongs to another peer')
                break
            except (RuntimeError, ValueError):
                if time.monotonic() > deadline:
                    raise
                time.sleep(1)
        print(json.dumps({'node': node['name'], 'status': 'tailnet-kubo-ready', 'peerId': node['peerId']}), flush=True)
    return nodes


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--nodes', required=True)
    p.add_argument('--output', required=True, help='private updated inventory; never commit it')
    p.add_argument('--approved-tailnet-service', action='store_true', required=True)
    args = p.parse_args()
    updated = install(json.loads(Path(args.nodes).read_text()))
    output = Path(args.output)
    output.write_text(json.dumps(updated, indent=2) + '\n')
    output.chmod(0o600)
