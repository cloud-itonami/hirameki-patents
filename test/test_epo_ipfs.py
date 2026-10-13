import pathlib
import sys
import unittest
sys.path.insert(0, str(pathlib.Path(__file__).parents[1] / 'scripts'))
from install_epo_ipfs import tailnet_host
from unittest.mock import patch
import hashlib
import subprocess
from epo_node import cid
import fetch_patent_peer


class ListenScope(unittest.TestCase):
    def test_explicit_tailnet_only(self):
        self.assertEqual('100.64.0.1', tailnet_host({'ssh': 'operator@100.64.0.1'}))
        self.assertEqual('100.127.255.254', tailnet_host({'ssh': '100.127.255.254'}))

    def test_wildcard_public_lan_and_loopback_refused(self):
        for host in ['0.0.0.0', '8.8.8.8', '192.168.1.3', '127.0.0.1', '100.128.0.1', '::']:
            with self.assertRaisesRegex(ValueError, 'explicit Tailnet'):
                tailnet_host({'ssh': 'operator@' + host})

    def test_unavailable_or_corrupt_peer_falls_back_with_integrity(self):
        data = b'{"schema":"fixture"}'
        nodes = [{'name': 'first'}, {'name': 'second'}]
        for first in [RuntimeError('unavailable'), subprocess.TimeoutExpired('ssh', 25), b'corrupted']:
            with patch.object(fetch_patent_peer, 'ssh', side_effect=[first, data]):
                received, receipt = fetch_patent_peer.fetch(nodes, cid(data), hashlib.sha256(data).hexdigest(), len(data))
                self.assertEqual(data, received)
                self.assertEqual('second', receipt['node'])
                self.assertEqual(['first'], receipt['failedPeers'])

    def test_no_peer_is_not_success(self):
        data = b'{"schema":"fixture"}'
        with self.assertRaisesRegex(RuntimeError, 'all patent peers unavailable'):
            fetch_patent_peer.fetch([], cid(data), hashlib.sha256(data).hexdigest(), len(data))


if __name__ == '__main__':
    unittest.main()
