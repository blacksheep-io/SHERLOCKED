"""Bounded local logging and non-overwriting export persistence."""
import json
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timezone
from pathlib import Path
import uuid
from .paths import ensure_directories, resource_path


def configure_logging():
    ensure_directories()
    logger=logging.getLogger('sherlocked')
    path=resource_path('logs')/'application.log'
    if not any(isinstance(handler,RotatingFileHandler) and Path(handler.baseFilename)==path for handler in logger.handlers):
        handler=RotatingFileHandler(path,maxBytes=2_000_000,backupCount=3,encoding='utf-8')
        handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(name)s %(message)s'))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)


def save_export(value,filename,metadata=None):
    directory=resource_path('exports'); directory.mkdir(parents=True,exist_ok=True)
    name=Path(filename).name
    if name!=filename or not name: raise ValueError('Export name must be a simple filename')
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:8]
    path=directory/f'{stamp}-{name}'
    payload=json.dumps(value,ensure_ascii=False,indent=2,default=str) if not isinstance(value,(str,bytes)) else value
    path.write_bytes(payload if isinstance(payload,bytes) else payload.encode('utf-8'))
    if metadata is not None:
        path.with_name(path.name+'.metadata.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    return path
