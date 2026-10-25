"""CPU-only demo configuration. Paths and limits never come from uploaded data."""
from dataclasses import dataclass
import os
from pathlib import Path

MODEL_ID = 'm-a-p/MERT-v1-95M'
REVISION = '12af15fef9d0ac838c3f475bfbbf26d2060dd4f5'
HEAD_SHA256 = '18a8f83c9ed879a6c214f8f21332a048dcf9196c2d8766f89b4cf35e6f3c469d'
CODE_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    model_dir: Path
    head_path: Path
    upload_dir: Path
    max_upload_bytes: int = 20 * 1024 * 1024
    max_duration_seconds: float = 90.0
    min_duration_seconds: float = 1.0
    max_queue_jobs: int = 3
    job_ttl_seconds: int = 3600
    inference_timeout_seconds: int = 1200
    max_job_records: int = 100
    cpu_threads: int = 2
    cors_origins: tuple[str, ...] = ('http://localhost:5173', 'http://127.0.0.1:5173')
    api_token: str = ''

    @classmethod
    def from_env(cls):
        return cls(
            model_dir=Path(os.getenv('MER_MODEL_DIR', str(CODE_ROOT / 'models' / 'mert'))).resolve(),
            head_path=Path(os.getenv('MER_HEAD_PATH', str(CODE_ROOT / 'models' / 'mean_mlp-seed20261011.pt'))).resolve(),
            upload_dir=Path(os.getenv('MER_UPLOAD_DIR', str(CODE_ROOT / '.runtime' / 'uploads'))).resolve(),
            cpu_threads=max(1, min(8, int(os.getenv('MER_CPU_THREADS', '2')))),
            api_token=os.getenv('MER_API_TOKEN', ''),
            cors_origins=tuple(s.strip() for s in os.getenv('MER_CORS_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173').split(',') if s.strip()),
        )
