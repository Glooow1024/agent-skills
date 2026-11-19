"""Validate and register an explicit service instance; never starts it."""
import argparse,json,re
from pathlib import Path
from core.backend import ROOT,read,write,registry,normalized

def validate(row,rows=()):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*',row.get('id','')):raise ValueError('Invalid unique instance id')
    for key in ('name','project','kind','group','description','entry','cwd','health','folder'):
        if not row.get(key):raise ValueError('Missing '+key)
    if not row.get('scripts'):raise ValueError('scripts must identify the actual worker')
    if not all(Path(p).is_absolute() for p in row['scripts']):raise ValueError('scripts must be absolute')
    for key in ('entry','cwd','health','folder','config','terminal'):
        if row.get(key) and not Path(row[key]).is_absolute():raise ValueError(key+' must be absolute')
    if row.get('kind') in ('message-bridge','knowledge-sync') or '/services/training-monitor/' in row['entry'].replace('\\','/'):
        if not row.get('config') or row.get('match_config')!=row['config']:raise ValueError('Shared workers require config and match_config')
    if row.get('autostart') and row['kind']!='message-bridge':raise ValueError('Login autostart is limited to explicitly configured bridges')
    for other in rows:
        if other['id']==row['id']:continue
        if row.get('terminal') and normalized(row['terminal'])==normalized(other.get('terminal','__none__')):raise ValueError('New instances must not reuse an old completion receipt')
        if row.get('config') and row['config']==other.get('config'):raise ValueError('Config is already registered')
        if row.get('kind')=='message-bridge' and other.get('kind')=='message-bridge':
            a=read(row['config']);b=read(other['config'])
            if a.get('runtime')==b.get('runtime'):raise ValueError('Bridges must not share queues')
            if (a.get('profile'),a.get('chat_id'))==(b.get('profile'),b.get('chat_id')):raise ValueError('Duplicate bridge route would execute commands twice')
    return row
def main():
    p=argparse.ArgumentParser();p.add_argument('--file',required=True);p.add_argument('--replace',action='store_true');p.add_argument('--check',action='store_true');a=p.parse_args()
    row=read(a.file);rows=registry();validate(row,rows)
    if any(s['id']==row['id'] for s in rows) and not a.replace:raise ValueError('ID exists; use --replace for an intentional update')
    if a.check:print('valid');return
    target=Path.home()/'.orbit/services.json'
    write(target,[s for s in rows if s['id']!=row['id']]+[row]);print('Registered; not started: '+row['id'])
if __name__=='__main__':main()
