import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from adapters import knowledge as k
from core.backend import write,read
class Tests(unittest.TestCase):
    def test_pause_and_dispatch(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);cfg=root/'config.json'
            write(cfg,dict(runtime=d,repository=str(root/'repo'),pythonw='pythonw.exe'))
            write(root/'state.json',dict(status='ok',message='已同步'))
            with patch.object(k,'CONFIG',cfg),patch.object(k,'processes',return_value=[]),patch.object(k.subprocess,'Popen') as spawn:
                self.assertEqual(k.state()['status'],'已同步')
                k.toggle_pause();self.assertTrue(k.state()['paused'])
                with self.assertRaises(RuntimeError):k.sync_now()
                spawn.assert_not_called()
                k.toggle_pause();k.sync_now()
                argv=spawn.call_args.args[0]
                self.assertEqual(argv[1:4],[str(k.SCRIPT),'sync','--now'])
                self.assertEqual(argv[-2:],['--config',str(cfg)])
                self.assertFalse(read(root/'pause.json')['paused'])
if __name__=='__main__':unittest.main()
