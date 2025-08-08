import json
import os
from datetime import datetime
from django.conf import settings


def _ensure_backups_dir() -> str:
    backups_dir = os.path.join(settings.BASE_DIR, 'backups')
    os.makedirs(backups_dir, exist_ok=True)
    return backups_dir


def log_change(model_name: str, action: str, payload):
    """Append a JSON line into backups/audit_log.jsonl with timestamp.

    - model_name: e.g., 'MainJobOperation'
    - action: e.g., 'delete', 'bulk_delete', 'update'
    - payload: dict or list that will be JSON-serialized
    """
    try:
        backups_dir = _ensure_backups_dir()
        log_path = os.path.join(backups_dir, 'audit_log.jsonl')
        entry = {
            'ts': datetime.utcnow().isoformat() + 'Z',
            'model': model_name,
            'action': action,
            'payload': payload,
        }
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    except Exception:
        # We intentionally swallow exceptions to never block the main flow
        pass



