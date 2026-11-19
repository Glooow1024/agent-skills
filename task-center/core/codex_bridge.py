"""Project-independent local Codex transport bootstrap."""
import socket,subprocess,time
from pathlib import Path
def ensure_bridge(log_dir):
    try:
        with socket.create_connection(('127.0.0.1',18773),timeout=2):return
    except OSError:pass
    cli=max((Path.home()/'AppData/Local/OpenAI/Codex/bin').glob('*/codex.exe'),key=lambda p:p.stat().st_mtime)
    with (log_dir/'bridge_restart.log').open('ab') as log:
        subprocess.Popen([str(cli),'app-server','--listen','ws://127.0.0.1:18773'],stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW)
