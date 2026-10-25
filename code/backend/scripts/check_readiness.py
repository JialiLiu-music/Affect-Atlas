"""Report environment/model readiness without loading neural weights."""
from pathlib import Path
import json
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import Settings, MODEL_ID, REVISION, HEAD_SHA256
from app.inference import asset_status, file_sha

settings = Settings.from_env()
ready, reason = asset_status(settings)
print(json.dumps({'device': 'cpu', 'ready': ready, 'reason': reason,
                  'model_id': MODEL_ID, 'revision': REVISION,
                  'model_directory_exists': settings.model_dir.is_dir(),
                  'head_exists': settings.head_path.is_file(),
                  'head_sha256_valid': file_sha(settings.head_path) == HEAD_SHA256 if settings.head_path.is_file() else False,
                  'next_step': 'Open http://localhost:5173 to upload a permitted audio excerpt.' if ready else 'Read code/README.md to prepare the verified source head and pinned MERT.'},
                 ensure_ascii=True, indent=2))
