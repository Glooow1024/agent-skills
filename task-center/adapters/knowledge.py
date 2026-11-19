"""Adapter for existing Knowledge Sync; retains its scheduler and Git rules."""
from core.backend import read,write,processes,registry,ROOT
from pathlib import Path
import subprocess
CONFIG=None
SCRIPT=ROOT.parent/'services/knowledge-sync/sync.py'
def selected(instance=None):
    if instance:return instance
    if CONFIG:return dict(config=str(CONFIG),entry=str(SCRIPT),scripts=[str(SCRIPT)],match_config=str(CONFIG))
    return next((s for s in registry() if s.get('kind')=='knowledge-sync'),{})
def config_path(instance=None):return selected(instance).get('config','__absent__')
def state(items=None,instance=None):
    instance=selected(instance)
    cfg=read(config_path(instance))
    if not cfg:return dict(status='未配置',message='未找到 Knowledge Sync 配置。',paused=False,running=False)
    runtime=Path(cfg['runtime']);s=read(runtime/'state.json');paused=read(runtime/'pause.json').get('paused',False)
    running=bool(processes(instance,items))
    names={'ok':'已同步','ready':'已检查','waiting':'等待编辑结束','pending':'等待同步','attention':'需要处理','paused':'已暂停','running':'正在同步'}
    return dict(status='已暂停' if paused else '正在同步' if running else names.get(s.get('status'),'等待首次同步'),
        message=s.get('message','尚无同步记录'),paused=paused,running=running,repository=cfg['repository'],runtime=str(runtime),
        checked_at=s.get('checked_at'),last_pull=s.get('last_pull'),last_push=s.get('last_push'),profile=cfg.get('profile'))
def toggle_pause(instance=None):
    cfg=read(config_path(instance));p=Path(cfg['runtime'])/'pause.json';value=not read(p).get('paused',False);write(p,dict(paused=value))
    return '自动同步已暂停；正在执行的同步会按原流程结束。' if value else '自动同步已恢复，将按原计划检查。'
def sync_now(instance=None):
    instance=selected(instance)
    s=state(instance=instance)
    if s['paused']:raise RuntimeError('请先恢复自动同步。')
    if s['running']:return '已有同步正在运行。'
    cfg=read(config_path(instance))
    subprocess.Popen([cfg['pythonw'],str(instance.get('entry',SCRIPT)),'sync','--now','--config',str(config_path(instance))],stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW)
    return '已发出同步请求，结果将在此页更新。'
