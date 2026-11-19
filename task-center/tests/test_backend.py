import unittest,tempfile
from pathlib import Path
from unittest.mock import patch
from core import backend as b

class Tests(unittest.TestCase):
    def test_completion_not_failure(self):
        with tempfile.TemporaryDirectory() as d,patch.object(b,'BASE',Path(d)):
            s=dict(id='test',scripts=[],terminal='stop.json')
            for reason,expected in [('verified_complete_notification_sent',True),('24h_monitor_limit_requires_review',False),('failed',False),('manual_stop',False)]:
                b.write(Path(d)/'stop.json',dict(reason=reason));self.assertEqual(b.finished(s),expected)
            b.write(Path(d)/'stop.json',dict(reason='verified_complete_notification_sent'))
            with patch.object(b,'processes',return_value=[]):self.assertTrue(b.snapshot(s)['hidden'])
            with self.assertRaises(RuntimeError):b.start(s)
    def test_process_match(self):
        import subprocess,sys
        with tempfile.TemporaryDirectory() as folder:
            script=Path(folder)/'worker.py'
            script.write_text('import time; time.sleep(30)')
            proc=subprocess.Popen([sys.executable,str(script)])
            try:
                self.assertIn(proc.pid,[p.pid for p in b.processes(dict(scripts=[str(script)]))])
                self.assertNotIn(proc.pid,[p.pid for p in b.processes(dict(scripts=[str(Path(folder)/'other'/'worker.py')]))])
            finally:
                proc.terminate();proc.wait(timeout=5)

if __name__=='__main__':unittest.main()
