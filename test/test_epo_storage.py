import importlib.util
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).parents[1] / 'scripts'))
import epo_monitor
import epo_publish
import epo_node


class CustodyTest(unittest.TestCase):
    def shard(self):
        return epo_node.canonical({'schema': 'epo-bibliography.v1', 'complete': False,
            'observations': [{'publication': {'id': 'EP-1000000-A1', 'authority': 'EP', 'title': ['green bricks'],
                 'publicationDate': None, 'applicationNumber': None, 'ipc': []},
                 'provenance': {'url': epo_node.BASE + '?_page=0', 'license': 'CC BY 4.0'}}]})

    def row(self, data):
        import hashlib
        return {'bytes': len(data), 'cid': epo_node.cid(data), 'sha256': hashlib.sha256(data).hexdigest()}

    def test_corruption_refused(self):
        data = self.shard()
        with self.assertRaisesRegex(ValueError, 'custody hash differs'):
            epo_publish.validate(data + b' ', self.row(data))

    def test_inventor_attribute_refused(self):
        import json
        obj = json.loads(self.shard())
        obj['observations'][0]['publication']['inventor'] = 'person'
        data = epo_node.canonical(obj)
        with self.assertRaisesRegex(ValueError, 'unscoped patent publication'):
            epo_publish.validate(data, self.row(data))

    def test_empty_shards_refused(self):
        data = epo_node.canonical({'schema': 'epo-bibliography.v1', 'complete': False, 'observations': []})
        with self.assertRaisesRegex(ValueError, 'invalid patent shard schema'):
            epo_publish.validate(data, self.row(data))

    def test_failed_projection_is_not_green(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory)
            (path / 'health.json').write_text('{"status":"failed"}')
            with self.assertRaisesRegex(ValueError, 'latest projection failed'):
                epo_monitor.check(path, [])


if __name__ == '__main__':
    unittest.main()
