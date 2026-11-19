"""Registry-driven login supervisor; never autostarts training."""
import msvcrt,sys,time
from core.backend import *
from core.codex_bridge import ensure_bridge

def main():
    lock=(DATA/'supervisor.lock').open('a+b');lock.write(b'0');lock.flush();lock.seek(0)
    try:msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
    except OSError:return
    if '--boot' in sys.argv:
        for s in registry():
            if s.get('autostart') and s.get('kind')=='message-bridge':paused(s).unlink(missing_ok=True)
    attempts={};last_bridge_check=0
    while True:
        try:
            services=registry();items=inventory()
            write(DATA/'status.json',dict(time=time.time(),services=[snapshot(s,items) for s in services]))
            for s in services:
                if s.get('kind')!='message-bridge' or not s.get('autostart') or paused(s).exists():continue
                if s.get('bootstrap_codex') and time.time()-last_bridge_check>60:
                    last_bridge_check=time.time();ensure_bridge(DATA)
                if not processes(s,items) and time.time()-attempts.get(s['id'],0)>60:
                    attempts[s['id']]=time.time();start(s)
            write(DATA/'supervisor_health.json',dict(pid=os.getpid(),heartbeat=time.time()))
        except Exception as e:write(DATA/'supervisor_error.json',dict(time=time.time(),error=str(e)))
        time.sleep(10)
if __name__=='__main__':main()
