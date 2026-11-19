"""Local binding editor using the bridge's shared schema, never the queue."""
import importlib.util
import json
import hashlib
import shutil
import tempfile
import os
import time
from pathlib import Path

source=Path(__file__).resolve().parents[2]/'services/message-bridge/routing.py'
spec=importlib.util.spec_from_file_location('orbit_routing',source)
routing=importlib.util.module_from_spec(spec);spec.loader.exec_module(routing)

def revision(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None

def load(service):
    config=json.loads(Path(service['config']).read_text(encoding='utf-8-sig'))
    path=routing.path(config)
    # Read once and fingerprint exactly the data displayed by the editor.
    raw=path.read_bytes() if path.exists() else None
    data=routing.validate(json.loads(raw.decode('utf-8-sig'))) if raw is not None else routing.load(config)
    return path,data,hashlib.sha256(raw).hexdigest() if raw is not None else None

def store(path,data,expected):
    routing.validate(data)
    if revision(path)!=expected:raise ValueError('绑定已被其他窗口修改，请关闭后重新打开。')
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():
        backup=path.parent/'binding-backups';backup.mkdir(exist_ok=True)
        shutil.copy2(path,backup/f'bindings-{time.time_ns()}.json')
    fd,name=tempfile.mkstemp(dir=path.parent,suffix='.tmp')
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as stream:json.dump(data,stream,ensure_ascii=False,indent=2)
        os.replace(name,path)
    finally:Path(name).unlink(missing_ok=True)
    return revision(path)
