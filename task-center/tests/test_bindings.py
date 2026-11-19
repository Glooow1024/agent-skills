import json
from pathlib import Path
import tempfile
import unittest
from adapters import bindings

class BindingTests(unittest.TestCase):
    def test_edit_backup_and_conflict(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);config=root/'config.json'
            config.write_text(json.dumps({'runtime':tmp,'thread_id':'legacy','secret_reference':'unchanged'}))
            original=config.read_bytes()
            path,data,version=bindings.load({'config':str(config)})
            self.assertEqual(data['tasks']['默认']['thread_id'],'legacy')
            version=bindings.store(path,data,version)
            data['tasks']['其他']={'thread_id':'other'}
            bindings.store(path,data,version)
            self.assertEqual(len(list((root/'binding-backups').glob('*.json'))),1)
            with self.assertRaises(ValueError):bindings.store(path,data,version)
            self.assertEqual(config.read_bytes(),original)
    def test_invalid_default_and_alias(self):
        for value in ({'tasks':{},'default':''},{'tasks':{'bad alias':{'thread_id':'id'}},'default':'bad alias'},
                      {'tasks':{'good':{'thread_id':'id'}},'default':'missing'}):
            with self.assertRaises(ValueError):bindings.routing.validate(value)
