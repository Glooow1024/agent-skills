"""Send to the explicitly configured bot profile and chat; no fallback destination."""
import json
import os
from pathlib import Path
import subprocess
import uuid

def send(text, config, idempotency_key=None):
    try:
        cfg=json.loads(Path(config).read_text(encoding='utf-8-sig'))
        if not cfg.get('enabled') or not cfg.get('chat_id'): return dict(ok=False,error='bridge_not_configured')
        cli=Path.home()/'AppData/Roaming/npm/node_modules/@larksuite/cli/scripts/run.js'
        p=subprocess.run(cfg.get('cli',['node',str(cli)])+['--profile',cfg['profile'],'im','+messages-send','--as','bot',
            '--chat-id',cfg['chat_id'],'--idempotency-key',idempotency_key or str(uuid.uuid4()),'--text','-'],
            input=text,capture_output=True,text=True,encoding='utf-8',timeout=35,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        r=json.loads(p.stdout)
        return dict(ok=p.returncode==0 and r.get('ok') is True,message_id=r.get('data',{}).get('message_id'),
            error=r.get('error',{}).get('subtype'))
    except Exception as e: return dict(ok=False,error=type(e).__name__)
