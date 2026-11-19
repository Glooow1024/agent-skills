import json
import tempfile
import unittest
from pathlib import Path
from core.setup_state import initialize


class Tests(unittest.TestCase):
    def test_fresh_install_has_no_active_services_and_rebased_examples(self):
        with tempfile.TemporaryDirectory(prefix='orbit setup ') as tmp:
            base=Path(tmp);repo=base/'repo with spaces';examples=repo/'examples';examples.mkdir(parents=True)
            (examples/'bridge.json').write_text(json.dumps({'enabled':False,'python':'C:/Python/python.exe','runtime':'C:/Users/YOU/.orbit/runtime/test','entry':'F:/Development/research/agent-skills/services/bridge.py'}))
            root=base/'profile'/'.orbit'
            initialize(root,repo,base/'python.exe')
            self.assertEqual(json.loads((root/'services.json').read_text()),[])
            sample=json.loads((root/'setup-examples/bridge.json').read_text())
            self.assertFalse(sample['enabled'])
            self.assertEqual(sample['python'],(base/'python.exe').as_posix())
            self.assertEqual(sample['entry'],repo.as_posix()+'/services/bridge.py')
            self.assertEqual(sample['runtime'],root.as_posix()+'/runtime/test')

    def test_reinstall_preserves_registry_drafts_and_unknown_settings(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);root=base/'.orbit';root.mkdir();repo=base/'repo';(repo/'examples').mkdir(parents=True)
            registry='[ {"id":"running","config":"private-path"} ]\n'
            (root/'services.json').write_text(registry)
            (root/'installation.json').write_text(json.dumps({'root':str(repo),'custom':'preserve'}))
            initialize(root,repo,base/'python.exe')
            self.assertEqual((root/'services.json').read_text(),registry)
            self.assertEqual(json.loads((root/'installation.json').read_text())['custom'],'preserve')
            (repo/'examples/example.json').write_text('{}')
            (root/'setup-examples/example.json').write_text('{"edited":true}')
            initialize(root,repo,base/'python.exe')
            self.assertTrue(json.loads((root/'setup-examples/example.json').read_text())['edited'])

    def test_invalid_state_or_relocation_fails_without_overwrite(self):
        for value in ('{broken','{}','[{"id":[]}]','[{"id":"same"},{"id":"same"}]'):
            with tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);p=root/'services.json';p.write_text(value)
                with self.assertRaises(ValueError):initialize(root,root/'repo',root/'python.exe')
                self.assertEqual(p.read_text(),value)
                self.assertFalse((root/'installation.json').exists())
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'services.json').write_text('[{"id":"active"}]')
            old=json.dumps({'root':str(root/'old')});(root/'installation.json').write_text(old)
            with self.assertRaises(ValueError):initialize(root,root/'new',root/'python.exe')
            self.assertEqual((root/'installation.json').read_text(),old)

if __name__=='__main__':unittest.main()
