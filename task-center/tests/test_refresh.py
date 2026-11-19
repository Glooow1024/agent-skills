import unittest
from unittest.mock import Mock
from ui.app import App,completed

class Tests(unittest.TestCase):
    def test_periodic_update_keeps_widgets(self):
        app=App.__new__(App);app.page='home';app.draw=Mock();app.updates=[Mock(),Mock()]
        for _ in range(5):app.update_values()
        app.draw.assert_not_called()
        self.assertEqual(app.updates[0].call_count,5)
    def test_history_only_rebuilds_on_membership_change(self):
        app=App.__new__(App);app.page='history';app.row_ids=('done',);app.draw=Mock();app.updates=[Mock()]
        app.cache={'done':dict(id='done',group='训练监测',hidden=True)}
        app.update_values();app.draw.assert_not_called()
        app.cache={};app.update_values();app.draw.assert_called_once()
    def test_completion_time(self):
        self.assertEqual(completed(0),'1970-01-01  08:00:00  北京时间')
        self.assertEqual(completed(None),'未记录完成时间')
if __name__=='__main__':unittest.main()
