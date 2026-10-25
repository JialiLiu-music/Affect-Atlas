"""Exercise the real spawn/pipe/terminate lifecycle with a test-only worker."""
from dataclasses import replace
import time
import pytest
from app.config import Settings
from app.inference import PredictionError
from app.worker import CpuWorker


def idle_test_process(connection, settings):
    try:
        connection.recv()
        time.sleep(30)
    except EOFError:
        pass
    finally:
        connection.close()


def test_cpu_worker_deadline_terminates_process(monkeypatch, tmp_path):
    settings = Settings(tmp_path/'mert', tmp_path/'head', tmp_path/'uploads')
    settings = replace(settings, inference_timeout_seconds=.2)
    monkeypatch.setattr('app.worker._serve', idle_test_process)
    worker = CpuWorker(settings)
    start = time.monotonic()
    try:
        with pytest.raises(PredictionError, match='超时'):
            worker.execute(tmp_path/'fixture.audio', lambda stage, progress: None)
        assert time.monotonic() - start < 10
        assert worker.process is None and worker.connection is None and worker.loaded is False
    finally:
        worker.close()
