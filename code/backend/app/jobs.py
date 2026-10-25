"""Bounded job queue and token-protected result records; no user filenames stored."""
import asyncio
from dataclasses import dataclass, field
from pathlib import Path
import secrets
import time
import uuid

from .config import Settings
from .inference import PredictionError
from .worker import CpuWorker


@dataclass
class Job:
    job_id: str
    access_token: str
    path: Path
    status: str = 'queued'
    stage: str = 'queued'
    progress: float = 0.
    result: dict | None = None
    error: str | None = None
    completed_at: float | None = None

    def public(self):
        return {k: getattr(self, k) for k in ['job_id', 'status', 'stage', 'progress', 'result', 'error']}


class QueueFull(Exception):
    pass


class JobManager:
    def __init__(self, settings: Settings, worker=None):
        self.settings = settings
        self.worker = worker or CpuWorker(settings)
        self.jobs: dict[str, Job] = {}
        self.queue = asyncio.Queue(maxsize=settings.max_queue_jobs)
        self.active = 0
        self.reservations = 0
        self.consumer = None
        self.cleaner = None
        self.closing = False

    async def start(self):
        self.settings.upload_dir.mkdir(parents=True, exist_ok=True)
        # Clear only this app's orphaned temporary files on local single-worker restart.
        for p in self.settings.upload_dir.glob('mer-upload-*.audio'):
            p.unlink(missing_ok=True)
        self.consumer = asyncio.create_task(self._consume())
        self.cleaner = asyncio.create_task(self._cleanup_loop())

    def reserve(self):
        self.prune()
        if self.closing or self.queue.qsize() + self.active + self.reservations >= self.settings.max_queue_jobs + 1:
            raise QueueFull()
        if len(self.jobs) + self.reservations >= self.settings.max_job_records:
            raise QueueFull()
        self.reservations += 1

    def release(self):
        self.reservations = max(0, self.reservations - 1)

    def submit(self, path: Path):
        job = Job(uuid.uuid4().hex, secrets.token_urlsafe(32), path)
        try:
            self.queue.put_nowait(job)
        except asyncio.QueueFull as exc:
            raise QueueFull() from exc
        self.jobs[job.job_id] = job
        return job

    def get(self, job_id, token):
        self.prune()
        job = self.jobs.get(job_id)
        if job is None or not secrets.compare_digest(job.access_token, token or ''):
            return None
        return job

    def prune(self):
        now = time.monotonic()
        for key in list(self.jobs):
            done = self.jobs[key].completed_at
            if done is not None and now - done > self.settings.job_ttl_seconds:
                self.jobs.pop(key, None)

    async def _cleanup_loop(self):
        while True:
            await asyncio.sleep(30)
            self.prune()

    async def _consume(self):
        while True:
            job = await self.queue.get()
            self.active = 1
            job.status = 'running'
            loop = asyncio.get_running_loop()
            def update(stage, progress):
                # Inference runs in a thread, mutations belong to the main loop.
                loop.call_soon_threadsafe(self._progress, job, stage, progress)
            try:
                result = await asyncio.to_thread(self.worker.execute, job.path, update)
                job.result = result
                job.status = job.stage = 'completed'
                job.progress = 1.
            except PredictionError as exc:
                job.status = job.stage = 'failed'
                job.error = str(exc)
            except asyncio.CancelledError:
                job.status = job.stage = 'failed'
                job.error = '服务已关闭，请重新提交。'
                raise
            except Exception:
                job.status = job.stage = 'failed'
                job.error = '任务处理失败，请重试。'
            finally:
                job.path.unlink(missing_ok=True)
                job.completed_at = time.monotonic()
                self.active = 0
                self.queue.task_done()

    @staticmethod
    def _progress(job, stage, progress):
        if job.status == 'running':
            job.stage = stage
            job.progress = min(.99, max(job.progress, float(progress)))

    async def close(self):
        self.closing = True
        self.worker.close()
        tasks = [t for t in [self.consumer, self.cleaner] if t is not None]
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        while not self.queue.empty():
            job = self.queue.get_nowait()
            job.path.unlink(missing_ok=True)
            self.queue.task_done()
