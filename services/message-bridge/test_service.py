import copy
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
from service import Bridge, accepted, save

class Tests(unittest.TestCase):
    def setUp(self):
        self.c=dict(enabled=True,owner_id='ou_owner',bot_id='ou_bot',chat_id='oc_group',thread_id='training',profile='test')
        self.e=dict(type='im.message.receive_v1',sender_type='user',sender_id='ou_owner',chat_type='group',chat_id='oc_group',
            message_type='text',message_id='om_one',mentions=[dict(id='ou_bot')],content='@助手 查询状态',create_time=str(int(time.time()*1000)))
    def test_filters(self):
        self.assertTrue(accepted(self.e,self.c))
        for k,v in dict(sender_type='bot',sender_id='ou_other',chat_id='oc_other',chat_type='p2p',mentions=[],message_type='post',create_time='0').items():
            e=copy.deepcopy(self.e);e[k]=v;self.assertFalse(accepted(e,self.c),k)
        c=dict(self.c,enabled=False);self.assertFalse(accepted(self.e,c))
    def test_new_message_and_serial_dispatch(self):
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as d:
            b=Bridge(self.c,Path(d));b.receive(self.e)
            self.assertFalse(b.receive(dict(self.e,event_id='redelivery')))
            self.assertTrue(b.receive(dict(self.e,message_id='om_two')))
            with patch.object(b,'reply',return_value=True), patch('service.subprocess.run',return_value=SimpleNamespace(stdout='{"state":"started","submission_id":"s1"}')) as wake:
                b.tick();self.assertEqual(wake.call_count,1)
                first=json.loads(b.db.execute('SELECT data FROM jobs WHERE id=?',('om_one',)).fetchone()[0])
                save(Path(d)/'acks'/f"{first['token']}.json",dict(request_id=first['token'],status='completed',text='完成'))
                first['next_try']=0;b.put(first)
                b.tick();self.assertEqual(wake.call_count,2)
            b.db.close()
    def test_restart_dedup_and_result_retry(self):
        with tempfile.TemporaryDirectory() as d:
            b=Bridge(self.c,Path(d));self.assertTrue(b.receive(self.e));b.db.close()
            b=Bridge(self.c,Path(d));self.assertFalse(b.receive(self.e))
            j=json.loads(b.db.execute('SELECT data FROM jobs').fetchone()[0]);j.update(state='started',received_sent=True);b.put(j)
            save(Path(d)/'acks'/f"{j['token']}.json",dict(request_id='wrong',status='completed',text='错误回执'))
            with patch.object(b,'reply') as r: b.tick();r.assert_not_called()
            save(Path(d)/'acks'/f"{j['token']}.json",dict(request_id=j['token'],status='needs_user',text='请选择恢复点'))
            with patch.object(b,'reply',return_value=False): b.tick()
            j=json.loads(b.db.execute('SELECT data FROM jobs').fetchone()[0]);self.assertNotEqual(j['state'],'done');j['next_try']=0;b.put(j)
            with patch.object(b,'reply',return_value=True) as r: b.tick();self.assertEqual(r.call_count,1)
            with patch.object(b,'reply') as r: b.tick();r.assert_not_called()
            self.assertEqual(json.loads(b.db.execute('SELECT data FROM jobs').fetchone()[0])['state'],'done');b.db.close()

if __name__=='__main__': unittest.main()
