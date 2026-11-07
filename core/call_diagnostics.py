"""Persistent, message-content-free diagnostics, including pythonw launches."""
from datetime import datetime,timezone
from pathlib import Path
import json,threading,os,sys
_lock=threading.Lock()
PATH=Path(__file__).resolve().parents[1]/'runtime/whatsapp-events.jsonl'

def event(kind,**fields):
    data=dict(at=datetime.now(timezone.utc).isoformat(),pid=os.getpid(),kind=kind,origin='test' if 'unittest' in Path(sys.argv[0]).parts or 'pytest' in Path(sys.argv[0]).name else 'application',**fields)
    try:
        PATH.parent.mkdir(parents=True,exist_ok=True)
        with _lock,PATH.open('a',encoding='utf-8') as out:out.write(json.dumps(data,ensure_ascii=False,default=str)+'\n')
    except Exception:pass
