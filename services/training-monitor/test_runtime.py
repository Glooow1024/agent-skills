import tempfile,unittest
from pathlib import Path
from unittest.mock import Mock
import runtime
class Tests(unittest.TestCase):
    def test_outbox_dedup_and_uncertain_send(self):
        s={};runtime.queue(s,'incident','first');runtime.queue(s,'incident','duplicate')
        self.assertEqual(s['outbox']['incident']['text'],'first')
        persist=Mock();send=Mock(return_value={'ok':True})
        runtime.flush(s,send,persist);runtime.flush(s,send,persist)
        send.assert_called_once();self.assertEqual(s['outbox']['incident']['status'],'sent')
        runtime.queue(s,'uncertain','text');s['outbox']['uncertain']['status']='sending'
        runtime.flush(s,send,persist);send.assert_called_once()
    def test_isolated_configs(self):
        import runner,json,sys,os
        original=os.getcwd();oldpath=sys.path[:]
        try:
            with tempfile.TemporaryDirectory() as d:
                root=Path(d);adapter=root/'adapter.py'
                adapter.write_text("from pathlib import Path\ndef configure(c):\n global cfg\n cfg=c\ndef main():\n Path(cfg['runtime']).joinpath('result').write_text(cfg['id'])\n")
                for name in ['one','two']:
                    state=root/name;state.mkdir();cfg=root/(name+'.json')
                    cfg.write_text(json.dumps(dict(id=name,adapter=str(adapter),cwd=d,runtime=str(state))))
                    runner.run(cfg)
                self.assertEqual((root/'one/result').read_text(),'one');self.assertEqual((root/'two/result').read_text(),'two')
        finally:os.chdir(original);sys.path[:]=oldpath
if __name__=='__main__':unittest.main()
