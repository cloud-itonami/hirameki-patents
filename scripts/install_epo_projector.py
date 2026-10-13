#!/usr/bin/env python3
"""Install a patent-only hourly GitHub projection using existing local gh auth."""
import argparse
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--runtime', required=True)
parser.add_argument('--nodes', required=True)
parser.add_argument('--commit', required=True)
parser.add_argument('--monitor-only', action='store_true')
args = parser.parse_args()
root = Path(args.runtime).resolve()
scripts = root / 'scripts'
scripts.mkdir(parents=True, exist_ok=True)
for name in ['epo_node.py', 'epo_publish.py', 'epo_monitor.py']:
    shutil.copy2(Path(__file__).parent / name, scripts / name)
nodes = root / 'nodes.json'
shutil.copy2(args.nodes, nodes)
nodes.chmod(0o600)
for directory in ['state', 'logs']:
    (root / directory).mkdir(exist_ok=True)
label = 'com.cloud-itonami.epo-projector'
body = {'Label': label, 'ProgramArguments': [sys.executable, str(scripts / 'epo_publish.py'),
    '--nodes', str(nodes), '--state', str(root / 'state'), '--commit', args.commit],
    'WorkingDirectory': str(root), 'StartInterval': 3600, 'RunAtLoad': True,
    'EnvironmentVariables': {'PATH': '/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin'},
    'StandardOutPath': str(root / 'logs/out.log'), 'StandardErrorPath': str(root / 'logs/err.log')}
path = Path.home() / 'Library/LaunchAgents' / (label + '.plist')
if path.exists() and not args.monitor_only:
    raise RuntimeError('existing projector definition; preserve and reconcile explicitly')
if not args.monitor_only:
    path.write_bytes(plistlib.dumps(body))
    subprocess.run(['launchctl', 'bootstrap', f'gui/{__import__("os").getuid()}', str(path)], check=True)
    print(str(path))
monitor_label = 'com.cloud-itonami.epo-monitor'
monitor = dict(body, Label=monitor_label, StartInterval=300,
    ProgramArguments=[sys.executable, str(scripts / 'epo_monitor.py'), '--nodes', str(nodes), '--state', str(root / 'state')],
    StandardOutPath=str(root / 'logs/monitor-out.log'), StandardErrorPath=str(root / 'logs/monitor-err.log'))
monitor_path = Path.home() / 'Library/LaunchAgents' / (monitor_label + '.plist')
if monitor_path.exists():
    raise RuntimeError('existing monitor definition; preserve and reconcile explicitly')
monitor_path.write_bytes(plistlib.dumps(monitor))
subprocess.run(['launchctl', 'bootstrap', f'gui/{__import__("os").getuid()}', str(monitor_path)], check=True)
print(str(monitor_path))
