"""Allowlisted local services only. Never launches remote training commands."""
import json, os, subprocess, sys, time, tempfile
from pathlib import Path
import psutil

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT
DATA=ROOT/'runtime'; DATA.mkdir(exist_ok=True)
PYTHON=Path(sys.executable).with_name('pythonw.exe')

def read(p,default=None):
    try:return json.loads(Path(p).read_text(encoding='utf-8-sig'))
    except (OSError,ValueError):return {} if default is None else default

def write(p,o):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(dir=p.parent,suffix='.tmp');t=Path(name)
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as out:json.dump(o,out,ensure_ascii=False,indent=2)
        for attempt in range(6):
            try:t.replace(p);break
            except PermissionError:
                if attempt==5:raise
                time.sleep(.05*(attempt+1))
    finally:t.unlink(missing_ok=True)

def registry():
    return read(Path.home()/'.orbit/services.json',[])

def normalized(p):return os.path.normcase(os.path.abspath(p))

def inventory():
    result=[]
    for p in psutil.process_iter(['pid','name']):
        try:
            if (p.info['name'] or '').lower() not in ('python.exe','pythonw.exe'):continue
            args=p.cmdline()
            paths=[]
            for arg in args[1:]:
                if arg.startswith('-') or not arg.lower().endswith('.py'):continue
                paths.append(normalized(arg if os.path.isabs(arg) else os.path.join(p.cwd(),arg)))
            result.append((p,paths))
        except (psutil.Error,OSError):pass
    return result

def processes(s,items=None):
    paths={normalized(BASE/x) for x in s['scripts']}
    result=[]
    for p,args in (inventory() if items is None else items):
        if not paths.intersection(args):continue
        try:
            required=s.get('match_config')
            if required and normalized(required) not in {normalized(a) for a in p.cmdline()[1:] if a.lower().endswith('.json')}:
                continue
            result.append(p)
        except psutil.Error:pass
    return result

def finished(s):
    marker=read(BASE/s.get('terminal','__absent__'))
    # Failure, expiration and manual stopping must remain visible.
    return marker.get('reason') in ('verified_complete_notification_sent','verified_complete')

def snapshot(s,items=None):
    procs=processes(s,items);h=read(BASE/s['health']) if s.get('health') else {}
    stamp=h.get('heartbeat',h.get('time',0))
    age=max(0,time.time()-stamp) if isinstance(stamp,(int,float)) and stamp else None
    done=finished(s)
    status='已完成，等待进程退出' if done and procs else '已完成' if done else '运行中' if procs else '已停止'
    if procs and (age is None or age>s.get('stale',660)):status='进程在运行，心跳待检查'
    if s.get('listener') and procs and not read(s['listener']).get('ready'):status='运行中，消息连接待恢复'
    if s.get('kind')=='knowledge-sync':
        cfg=read(s['config']);is_paused=read(Path(cfg['runtime'])/'pause.json').get('paused',False)
        status='已暂停' if is_paused else '正在同步' if procs else {'ok':'已同步','attention':'需要处理','waiting':'等待编辑结束','ready':'已检查'}.get(h.get('status'),'等待计划执行')
    terminal=read(BASE/s.get('terminal','__absent__'))
    return dict(**s,status=status,pids=[p.pid for p in procs],age=age,done=done,hidden=done and not procs,
        completed_at=terminal.get('time') if done else None)

def paused(s):return DATA/(s['id']+'.paused')

def start(s):
    if finished(s):raise RuntimeError('该任务已完成，请为新实验注册独立入口。')
    if processes(s):return '已在运行，无需重复启动。'
    paused(s).unlink(missing_ok=True)
    if s.get('stop_request'):Path(s['stop_request']).unlink(missing_ok=True)
    if s.get('manual_flag'):(BASE/s['manual_flag']).unlink(missing_ok=True)
    log=(DATA/(s['id']+'.log')).open('ab')
    try:
        p=subprocess.Popen([str(PYTHON),str(BASE/s['entry'])]+s.get('args',[]),cwd=s.get('cwd',str(BASE)),stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW)
    finally:log.close()
    write(DATA/(s['id']+'.launch.json'),dict(pid=p.pid,time=time.time()))
    return '已发出启动请求；请以随后显示的进程和心跳为准。'

def stop(s):
    paused(s).write_text(str(time.time()))
    if s.get('manual_flag'):(BASE/s['manual_flag']).write_text('manual stop from local console')
    if s.get('stop_request'):
        Path(s['stop_request']).write_text('manual stop')
        deadline=time.time()+40
        while processes(s) and time.time()<deadline:time.sleep(.3)
        if processes(s):raise RuntimeError('已请求停止，进程尚未退出，请检查日志。')
    else:
        # Stop supervisors first so workers cannot be respawned. Match full script paths.
        for script in s['scripts']:
            selected=dict(s,scripts=[script])
            for p in processes(selected):
                try:
                    created=p.create_time()
                    p.suspend()
                    children=p.children(recursive=True)
                    if p.create_time()!=created:raise RuntimeError('进程身份发生变化')
                    for child in reversed(children):
                        try:child.terminate()
                        except psutil.NoSuchProcess:pass
                    p.terminate();psutil.wait_procs(children+[p],timeout=5)
                except psutil.NoSuchProcess:pass
    write(DATA/(s['id']+'.manual_stop.json'),dict(time=time.time(),remaining=[p.pid for p in processes(s)]))
    return '本地服务已停止。' if not processes(s) else '停止尚未完成，请检查进程。'
