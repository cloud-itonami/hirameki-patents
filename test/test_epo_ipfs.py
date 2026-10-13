import pathlib
import sys
import unittest
sys.path.insert(0, str(pathlib.Path(__file__).parents[1] / 'scripts'))
from install_epo_ipfs import tailnet_host


class ListenScope(unittest.TestCase):
    def test_explicit_tailnet_only(self):
        self.assertEqual('100.64.0.1', tailnet_host({'ssh': 'operator@100.64.0.1'}))
        self.assertEqual('100.127.255.254', tailnet_host({'ssh': '100.127.255.254'}))

    def test_wildcard_public_lan_and_loopback_refused(self):
        for host in ['0.0.0.0', '8.8.8.8', '192.168.1.3', '127.0.0.1', '100.128.0.1', '::']:
            with self.assertRaisesRegex(ValueError, 'explicit Tailnet'):
                tailnet_host({'ssh': 'operator@' + host})


if __name__ == '__main__':
    unittest.main()
