"""Finite local worker supervisor. Never starts a training command."""
import argparse,sys,subprocess,time,msvcrt,os
from pathlib import Path
from runtime import load,save
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--config',required=True);args=parser.parse_args();c=load(args.config)
    root=Path(c['runtime']);root.mkdir(parents=True,exist_ok=True)
    lock=(root/'guard.lock').open('a+b');lock.write(b'0');lock.flush();lock.seek(0)
    try:msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
    except OSError:return
    start=time.time();restarts=0
    while time.time()-start<c.get('max_seconds',7*86400):
        if any(Path(p).exists() for p in c.get('stop_markers',[])):return
        with (root/'watch.log').open('ab') as log:
            child=subprocess.Popen([sys.executable,str(Path(__file__).with_name('runner.py')),'--config',args.config],cwd=c['cwd'],stdout=log,stderr=log,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            while child.poll() is None:
                save(root/'guard.json',dict(pid=os.getpid(),child_pid=child.pid,heartbeat=time.time(),restarts=restarts));time.sleep(10)
        if any(Path(p).exists() for p in c.get('stop_markers',[])):return
        restarts+=1
        if restarts>=c.get('max_restarts',3):
            save(root/'guard_failed.json',dict(time=time.time(),exit_code=child.returncode,restarts=restarts));return
        time.sleep(c.get('restart_delay',60))
    save(root/'expired.json',dict(time=time.time(),reason='monitor_limit_requires_review'))
if __name__=='__main__':main()
