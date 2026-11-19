"""Configured project adapter runner; no project paths or recipes."""
import argparse,os,sys
from pathlib import Path
from runtime import load,module
def run(config,once=False):
    cfg=load(config)
    for key in ('id','adapter','cwd','runtime'):
        if not cfg.get(key):raise ValueError('Missing monitor setting: '+key)
    for key in ('adapter','cwd','runtime'):
        if not Path(cfg[key]).is_absolute():raise ValueError(key+' must be absolute')
    old_cwd=os.getcwd();old_path=sys.path[:];old_argv=sys.argv[:]
    try:
        os.chdir(cfg['cwd']);sys.path.insert(0,str(Path(cfg['adapter']).parent))
        adapter=module(cfg['adapter'],'orbit_project_adapter')
        if not callable(getattr(adapter,'configure',None)):raise ValueError('Adapter must expose configure(config) and main()')
        adapter.configure(cfg)
        if once and '--once' not in sys.argv:sys.argv.append('--once')
        adapter.main()
    finally:os.chdir(old_cwd);sys.path[:]=old_path;sys.argv[:]=old_argv
def main():
    p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--once',action='store_true');a=p.parse_args();run(a.config,a.once)
if __name__=='__main__':main()
