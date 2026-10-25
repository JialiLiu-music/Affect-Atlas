"""Local research demo API. Run exactly ONE uvicorn worker, default loopback."""
from contextlib import asynccontextmanager
from pathlib import Path
import secrets
import uuid

from fastapi import FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .config import Settings, MODEL_ID, REVISION
from .inference import asset_status
from .jobs import JobManager, QueueFull

EXTENSIONS = {'.wav', '.mp3', '.flac', '.ogg'}


def create_app(settings=None, worker=None, readiness=None):
    settings = settings or Settings.from_env()
    manager = JobManager(settings, worker)
    status_check = readiness or asset_status

    @asynccontextmanager
    async def lifespan(app):
        await manager.start()
        try:
            yield
        finally:
            await manager.close()

    app = FastAPI(title='Music Emotion CPU Demo', version='1.0.0', lifespan=lifespan)
    app.state.manager = manager
    from .middleware import UploadBoundaryMiddleware
    app.add_middleware(UploadBoundaryMiddleware, max_bytes=settings.max_upload_bytes,
                       capacity=settings.max_queue_jobs + 1, api_token=settings.api_token)
    app.add_middleware(CORSMiddleware, allow_origins=list(settings.cors_origins),
                       allow_credentials=False, allow_methods=['GET', 'POST'],
                       allow_headers=['Content-Type', 'X-Job-Token', 'Authorization'])

    def authorize(header):
        if settings.api_token and not secrets.compare_digest(header or '', 'Bearer ' + settings.api_token):
            raise HTTPException(401, '需要有效的演示访问令牌。')

    @app.get('/api/health')
    async def health():
        available, reason = status_check(settings)
        return dict(status='ready' if available else 'not_ready', device='cpu',
                    model=dict(loaded=manager.worker.loaded, assets_available=available,
                               reason=reason, model_id=MODEL_ID, revision=REVISION, head_seed=20261011),
                    limits=dict(max_upload_bytes=settings.max_upload_bytes,
                                max_duration_seconds=settings.max_duration_seconds,
                                min_duration_seconds=settings.min_duration_seconds,
                                max_queue_jobs=settings.max_queue_jobs,
                                job_ttl_seconds=settings.job_ttl_seconds),
                    queue=dict(active=manager.active, queued=manager.queue.qsize()),
                    prediction_task='overall_static_valence_arousal', calibration='none')

    @app.post('/api/jobs', status_code=202)
    async def upload(file: UploadFile = File(...), authorization: str | None = Header(default=None)):
        path = None
        reserved = False
        submitted = False
        try:
            authorize(authorization)
            available, reason = status_check(settings)
            if not available:
                raise HTTPException(503, reason)
            suffix = Path(file.filename or '').suffix.lower()
            if suffix not in EXTENSIONS:
                raise HTTPException(415, '仅支持WAV、MP3、FLAC和OGG；M4A请先转换格式。')
            try:
                manager.reserve()
                reserved = True
            except QueueFull:
                raise HTTPException(429, '任务队列已满，请稍后重试。')
            # UUID filename and exclusive open: no user path, no overwrites.
            path = settings.upload_dir / ('mer-upload-' + uuid.uuid4().hex + '.audio')
            size = 0
            with path.open('xb') as output:
                while chunk := await file.read(65536):
                    size += len(chunk)
                    if size > settings.max_upload_bytes:
                        raise HTTPException(413, '音频文件超过20MB限制。')
                    output.write(chunk)
            if size == 0:
                raise HTTPException(400, '上传文件为空。')
            try:
                job = manager.submit(path)
            except QueueFull:
                raise HTTPException(429, '任务队列已满，请稍后重试。')
            submitted = True
            return dict(job_id=job.job_id, access_token=job.access_token, status=job.status)
        finally:
            await file.close()
            if reserved:
                manager.release()
            if path is not None and not submitted:
                path.unlink(missing_ok=True)

    @app.get('/api/jobs/{job_id}')
    async def job_status(job_id: str, x_job_token: str | None = Header(default=None),
                         authorization: str | None = Header(default=None)):
        authorize(authorization)
        job = manager.get(job_id, x_job_token)
        if job is None:
            raise HTTPException(404, '任务不存在、已过期或访问令牌无效。')
        return job.public()

    return app


app = create_app()
