import json
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from routing import Router
from service import Bridge, save

class RoutingTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.c=dict(enabled=True,owner_id='owner',bot_id='bot',chat_id='group',thread_id='legacy',profile='test',runtime=str(self.root))
        self.bindings={'default':'多视角','tasks':{'多视角':{'thread_id':'multi'},'单视角':{'thread_id':'single'},'同一聊天':{'thread_id':'single'}}}
        save(self.root/'bindings.json',self.bindings)
    def tearDown(self):self.tmp.cleanup()
    def event(self,body,ident='one'):
        return dict(type='im.message.receive_v1',sender_type='user',sender_id='owner',chat_type='group',chat_id='group',
                    message_type='text',message_id='om_'+ident,mentions=[{'id':'bot','key':'@_user_1'}],content=json.dumps({'text':'@_user_1 '+body}),create_time=str(int(time.time()*1000)))
    def test_commands_expiry_restart_and_binding_change(self):
        r=Router(self.c)
        self.assertEqual(r.route(self.event('状态'),0)['thread_id'],'multi')
        self.assertIn('/发',r.route(self.event('/help'),0)['control'])
        self.assertIn('单视角',r.route(self.event('/任务'),0)['control'])
        r.route(self.event('/切换 单视角'),0)
        self.assertEqual(r.route(self.event('/发 多视角 检查\n损失'),1)['body'],'检查\n损失')
        self.assertEqual(r.route(self.event('状态'),2)['thread_id'],'single')
        self.assertIn('control',r.route(self.event('状态'),1801))
        self.assertIn('control',Router(self.c).route(self.event('状态'),3))
        r.route(self.event('/切换 单视角'),4)
        self.bindings['tasks']['单视角']['thread_id']='changed';save(self.root/'bindings.json',self.bindings)
        self.assertIn('control',r.route(self.event('状态'),5))
        r.route(self.event('/清除'),6)
        self.assertEqual(Router(self.c).route(self.event('状态'),7)['thread_id'],'multi')
        for body in ('/发 不存在 hello','/发 单视角','/切换 不存在','/错误'):
            self.assertIn('control',r.route(self.event(body),8))
    def test_duplicate_switch_cannot_reset_selection(self):
        b=Bridge(self.c)
        try:
            event=self.event('/切换 单视角');b.receive(event)
            b.receive(self.event('/切换 多视角','two'));self.assertFalse(b.receive(event))
            b.receive(self.event('执行','three'))
            job=json.loads(b.db.execute('SELECT data FROM jobs WHERE id=?',('om_three',)).fetchone()[0])
            self.assertEqual(job['route']['thread_id'],'multi')
            other=self.event('/切换 单视角','intruder');other['sender_id']='other'
            self.assertFalse(b.receive(other))
        finally:b.db.close()
    def test_frozen_targets_parallel_chats_and_labeled_results(self):
        b=Bridge(self.c)
        try:
            for text,ident in [('/发 单视角 first','one'),('/发 多视角 second','two'),('/发 同一聊天 third','three'),('/help','help')]:b.receive(self.event(text,ident))
            self.bindings['tasks']['单视角']['thread_id']='changed';save(self.root/'bindings.json',self.bindings)
            with patch.object(b,'reply',return_value=True) as replies,patch('service.subprocess.run',return_value=SimpleNamespace(stdout='{"state":"started"}')) as wake:
                b.tick();self.assertEqual(wake.call_count,2)
                job=json.loads(b.db.execute('SELECT data FROM jobs WHERE id=?',('om_one',)).fetchone()[0])
                request=json.loads((self.root/'requests'/f"{job['token']}.json").read_text(encoding='utf-8'))
                self.assertEqual(request['thread_id'],'single');self.assertIn('first',request['message'])
                self.assertTrue(any('【单视角】' in call.args[2] for call in replies.call_args_list))
                save(self.root/'acks'/f"{job['token']}.json",dict(request_id=job['token'],status='completed',text='结果'))
                job['next_try']=0;b.put(job);b.tick()
                self.assertTrue(any('【单视角】[completed]' in call.args[2] for call in replies.call_args_list))
        finally:b.db.close()
    def test_legacy_queue_preserves_request_target_and_done_rows(self):
        b=Bridge(self.c);b.receive(self.event('old'));job=json.loads(b.db.execute('SELECT data FROM jobs').fetchone()[0])
        del job['route'];b.put(job)
        save(self.root/'requests'/f"{job['token']}.json",{'thread_id':'original','endpoint':'ws://localhost:1234'})
        done=dict(job,id='om_done',state='done');b.put(done)
        before=b.db.execute('SELECT data FROM jobs WHERE id=?',('om_done',)).fetchone()[0];b.db.close()
        b=Bridge(self.c)
        try:
            migrated=json.loads(b.db.execute('SELECT data FROM jobs WHERE id=?',('om_one',)).fetchone()[0])
            self.assertEqual(migrated['route']['thread_id'],'original')
            self.assertEqual(migrated['token'],job['token'])
            self.assertEqual(b.db.execute('SELECT data FROM jobs WHERE id=?',('om_done',)).fetchone()[0],before)
        finally:b.db.close()
    def test_control_retry_restart_and_corrupt_bindings_never_dispatch(self):
        b=Bridge(self.c);b.receive(self.event('/help'))
        with patch.object(b,'reply',return_value=False),patch('service.subprocess.run') as wake:
            b.tick();wake.assert_not_called()
        job=json.loads(b.db.execute('SELECT data FROM jobs').fetchone()[0]);job['next_try']=0;b.put(job);b.db.close()
        b=Bridge(self.c)
        try:
            (self.root/'bindings.json').write_text('{broken',encoding='utf-8')
            b.receive(self.event('must not dispatch','bad'))
            with patch.object(b,'reply',return_value=True),patch('service.subprocess.run') as wake:
                b.tick();wake.assert_not_called()
            self.assertTrue(all(json.loads(row[0])['state']=='done' for row in b.db.execute('SELECT data FROM jobs')))
        finally:b.db.close()
    def test_unavailable_target_blocks_only_its_own_later_commands(self):
        b=Bridge(self.c)
        try:
            b.receive(self.event('/发 单视角 first','first'))
            b.receive(self.event('/发 单视角 second','second'))
            b.receive(self.event('/发 多视角 independent','third'))
            with patch.object(b,'reply',return_value=True),patch('service.subprocess.run',return_value=SimpleNamespace(stdout='{"state":"unavailable"}')) as wake:
                b.tick();self.assertEqual(wake.call_count,2)
            second=json.loads(b.db.execute('SELECT data FROM jobs WHERE id=?',('om_second',)).fetchone()[0])
            self.assertEqual(second['state'],'pending')
        finally:b.db.close()

if __name__=='__main__':unittest.main()
