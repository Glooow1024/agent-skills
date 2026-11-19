"""Explicit owner-only routing; bindings are separate from credentials and queues."""
import json
import re
from urllib.parse import urlsplit
from pathlib import Path

HELP = ('【控制群帮助】所有消息都需要本人 @机器人。\n'
        '/任务：列出绑定任务和当前选择\n'
        '/发 <任务别名> <指令>：仅本条发到指定聊天\n'
        '/切换 <任务别名>：临时选择任务，有效期30分钟\n'
        '/清除：取消临时选择，恢复默认任务\n'
        '/help 或 /帮助：显示帮助\n'
        '普通文本：发给当前临时选择或默认任务。临时选择过期、重启或绑定变更后须重新选择或 /清除。\n'
        '绑定管理：Orbit → 消息桥接 → 服务详情 → 管理任务绑定。')

def path(config):
    return Path(config.get('bindings_file') or Path(config['runtime'])/'bindings.json')

def validate(value):
    if not isinstance(value, dict) or not isinstance(value.get('tasks'), dict):
        raise ValueError('绑定必须包含 tasks 对象')
    tasks=value['tasks']
    if not tasks or len(tasks)>100:
        raise ValueError('请保留1至100个任务')
    for alias, target in tasks.items():
        if not isinstance(alias,str) or not re.fullmatch(r'[^\s/]{1,40}',alias):
            raise ValueError('任务别名须为1至40字，不能含空格或斜杠')
        if not isinstance(target,dict) or not isinstance(target.get('thread_id'),str) or not target['thread_id'].strip():
            raise ValueError('每个任务都需要聊天 ID')
        if any(ch.isspace() for ch in target['thread_id']):
            raise ValueError('聊天 ID 不能含空白')
        if 'endpoint' in target:
            if not isinstance(target['endpoint'],str) or urlsplit(target['endpoint']).scheme not in ('ws','wss') or not urlsplit(target['endpoint']).hostname:
                raise ValueError('endpoint 必须是有效的 ws:// 或 wss:// 地址')
    if value.get('default') not in tasks:
        raise ValueError('默认任务必须存在于任务列表')
    return value

def load(config):
    source=path(config)
    if source.exists():
        return validate(json.loads(source.read_text(encoding='utf-8-sig')))
    return validate({'default':'默认','tasks':{'默认':{'thread_id':config['thread_id']}}})

def content(event):
    value=event['content']
    try:
        parsed=json.loads(value)
        if isinstance(parsed,dict) and isinstance(parsed.get('text'),str):value=parsed['text']
    except ValueError:pass
    # Only remove the leading platform mention, not arbitrary text within the command.
    for mention in event.get('mentions',[]):
        for token in (mention.get('key'), '@'+mention.get('name','') if mention.get('name') else None):
            if token and value.lstrip().startswith(token):value=value.lstrip()[len(token):]
    value=re.sub(r'^\s*@_user_\d+\s*','',value)
    return value.strip()

class Router:
    def __init__(self,config):
        self.config=config
        self.selection=None
        # A persisted marker prevents restart silently rerouting ordinary text to default.
        self.marker=Path(config['runtime'])/'selection-used.json'
        self.requires_selection=self.marker.exists()

    def route(self,event,now):
        bindings=load(self.config);tasks=bindings['tasks'];raw=content(event)
        parts=raw.split(maxsplit=2);command=parts[0] if parts else ''
        if command in ('/help','/帮助'):return {'control':HELP}
        if command=='/任务':
            selected=self.selection
            current=selected[0] if selected and now<selected[2] and tasks.get(selected[0])==selected[1] else ('待重新选择' if self.requires_selection else bindings['default'])
            return {'control':'【任务列表】\n'+'\n'.join('• '+a+('（默认）' if a==bindings['default'] else '') for a in tasks)+'\n当前：'+current}
        if command=='/清除':
            self.selection=None;self.requires_selection=False;self.marker.unlink(missing_ok=True)
            return {'control':'【控制群】已取消临时选择；默认任务：'+bindings['default']}
        if command=='/切换':
            if len(parts)!=2 or parts[1] not in tasks:return {'control':'【控制群】请使用 /切换 <已绑定别名>；/任务 查看列表。'}
            alias=parts[1]
            self.marker.parent.mkdir(parents=True,exist_ok=True)
            self.marker.write_text('{}',encoding='utf-8')
            self.selection=(alias,dict(tasks[alias]),now+1800);self.requires_selection=True
            return {'control':f'【{alias}】已切换，有效期30分钟。/发 不改变此选择。'}
        if command=='/发':
            if len(parts)!=3 or parts[1] not in tasks:return {'control':'【控制群】请使用 /发 <已绑定别名> <指令>；/任务 查看列表。'}
            alias=parts[1];body=parts[2]
        elif command.startswith('/'):
            return {'control':'【控制群】未知命令，请发送 /help。'}
        else:
            alias=bindings['default'];body=raw
            if self.requires_selection:
                if not self.selection or now>=self.selection[2] or tasks.get(self.selection[0])!=self.selection[1]:
                    return {'control':'【控制群】临时选择已失效。请 /切换 <任务>、/发 <任务> <指令> 或 /清除 恢复默认。'}
                alias=self.selection[0]
        if not body:return {'control':'【控制群】请输入指令，或发送 /help。'}
        return {'alias':alias,'thread_id':tasks[alias]['thread_id'],
                'endpoint':tasks[alias].get('endpoint',self.config.get('endpoint','ws://127.0.0.1:18773')),'body':body}
