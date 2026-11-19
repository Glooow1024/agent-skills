"""Reusable monitor primitives; project adapters own evidence and policy."""
import json,time,importlib.util
from pathlib import Path
def load(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def save(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix('.tmp');temp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8');temp.replace(path)
def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path);obj=importlib.util.module_from_spec(spec);spec.loader.exec_module(obj);return obj
def queue(state,key,text):
    state.setdefault('outbox',{}).setdefault(key,dict(text=text,status='pending',attempts=0,next_try=0))
def flush(state,send,persist,now=time.time):
    for key,row in state.get('outbox',{}).items():
        # Persisted sending without a receipt is uncertain; never blindly resend.
        if row['status'] not in ('pending','retry') or now()<row['next_try']:continue
        row.update(status='sending',attempts=row['attempts']+1);persist(state)
        try:result=send(row['text'])
        except Exception as exc:result=dict(ok=False,error=type(exc).__name__)
        row['receipt']=result;row['status']='sent' if result.get('ok') else ('exhausted' if row['attempts']>=5 else 'retry')
        row['next_try']=now()+min(3600,60*2**row['attempts']);persist(state)
def sender(config):
    notify=module(Path(__file__).resolve().parents[1]/'message-bridge/notify.py','orbit_notify')
    return lambda text:notify.send(text,config)
def wait(interval,runtime):
    deadline=time.monotonic()+interval
    while time.monotonic()<deadline:
        marker=Path(runtime)/'reload.request'
        if marker.exists():marker.unlink();return False
        time.sleep(min(1,max(0,deadline-time.monotonic())))
    return True
