import importlib.util
import pathlib
import unittest

spec = importlib.util.spec_from_file_location('epo_node', pathlib.Path(__file__).parents[1] / 'scripts/epo_node.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class ParseTest(unittest.TestCase):
    def row(self):
        return {'_about': 'http://data.epo.org/linked-data/data/publication/EP/1000000/A1/-',
                'publicationAuthority': {'_about': 'http://data.epo.org/linked-data/id/st3/EP'},
                'publicationKind': {'label': 'A1'}, 'label': 'EP 1000000 A1',
                'titleOfInvention': ['Green bricks'], 'inventor': {'name': 'MUST NOT PUBLISH'}}

    def test_public_subset(self):
        out = mod.parse({'format': 'linked-data-api', 'result': {'items': [self.row()]}}, mod.BASE, 'now')
        self.assertEqual('EP-1000000-A1', out[0]['publication']['id'])
        self.assertNotIn(b'MUST NOT PUBLISH', mod.canonical(out))

    def test_empty_fails(self):
        with self.assertRaisesRegex(ValueError, 'empty or malformed'):
            mod.parse({'format': 'linked-data-api', 'result': {'items': []}}, mod.BASE, 'now')

    def test_identity_fails(self):
        row = self.row()
        row['label'] = 'EP 1000000 B1'
        with self.assertRaisesRegex(ValueError, 'contradictory EP identity'):
            mod.parse({'format': 'linked-data-api', 'result': {'items': [row]}}, mod.BASE, 'now')

    def test_live_uri_and_single_classification(self):
        row = self.row()
        row['application'] = 'http://data.epo.org/linked-data/id/application/EP/99402631'
        row['classificationIPCInventive'] = {'label': 'G03B 21/00'}
        out = mod.parse({'format': 'linked-data-api', 'result': {'items': [row]}}, mod.BASE, 'now')[0]['publication']
        self.assertEqual('99402631', out['applicationNumber'])
        self.assertEqual(['G03B 21/00'], out['ipc'])

    def test_shard_bound(self):
        with self.assertRaisesRegex(ValueError, 'oversized shard'):
            mod.store(None, b'x' * (mod.LIMIT + 1))


if __name__ == '__main__':
    unittest.main()
