"""Create editable experiment templates only; never launches or contacts services."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys

ASSETS = Path(__file__).resolve().parents[1]/'assets'

def initialize(output, run_id, thread_id=None):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,95}', run_id):
        raise ValueError('run-id仅允许字母/数字及_.-，首位为字母或数字，最长96字符')
    if thread_id and not re.fullmatch(r'[A-Za-z0-9_-]{1,128}',thread_id):
        raise ValueError('thread-id包含不允许字符')
    output=Path(output).resolve()
    if output.exists():
        raise ValueError('目标已存在；为避免覆盖，请选择新的实验文档目录')
    values={'{{RUN_ID}}':run_id,'{{THREAD_ID}}':thread_id or '待填写本次聊天ID',
            '{{CREATED_AT}}':datetime.now(timezone.utc).isoformat()}
    prepared={}
    for source in sorted(ASSETS.iterdir()):
        if not source.is_file():continue
        text=source.read_text(encoding='utf-8')
        for old,new in values.items():text=text.replace(old,new)
        if source.suffix=='.json':
            document=json.loads(text)
            if not thread_id:document['monitoring']['thread_id']=None
            text=json.dumps(document,ensure_ascii=False,indent=2)+'\n'
        prepared[source.name]=text
    if not prepared:raise ValueError('模板目录为空')
    output.mkdir(parents=True,exist_ok=False)
    for name,text in prepared.items():(output/name).write_text(text,encoding='utf-8')
    return {'directory':str(output),'run_id':run_id,'files':list(prepared),
            'ready_for_training':False,'training_started':False,'notifications_sent':False}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True)
    parser.add_argument('--run-id',required=True)
    parser.add_argument('--thread-id')
    args=parser.parse_args()
    try:result=initialize(args.output,args.run_id,args.thread_id)
    except (ValueError,OSError) as error:
        print(str(error),file=sys.stderr);return 1
    print(json.dumps(result,ensure_ascii=False,indent=2));return 0

if __name__=='__main__':raise SystemExit(main())
