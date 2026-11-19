import unittest,tempfile
from pathlib import Path
from unittest.mock import Mock
from core import backend as b
class Tests(unittest.TestCase):
    def test_shared_script_does_not_match_other_config(self):
        with tempfile.TemporaryDirectory() as d:
            script=str(Path(d)/'service.py');a=str(Path(d)/'a.json');other=str(Path(d)/'b.json')
            first=Mock();first.cmdline.return_value=['python',script,'--config',a]
            second=Mock();second.cmdline.return_value=['python',script,'--config',other]
            rows=[(first,[b.normalized(script)]),(second,[b.normalized(script)])]
            self.assertEqual(b.processes(dict(scripts=[script],match_config=a),rows),[first])
    def test_running_completed_task_not_hidden(self):
        with tempfile.TemporaryDirectory() as d:
            marker=Path(d)/'stop.json';b.write(marker,dict(reason='verified_complete_notification_sent',time=1))
            from unittest.mock import patch
            with patch.object(b,'processes',return_value=[Mock(pid=1)]):
                self.assertFalse(b.snapshot(dict(scripts=[],terminal=str(marker)))['hidden'])
if __name__=='__main__':unittest.main()
