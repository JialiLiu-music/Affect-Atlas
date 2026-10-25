"""API safety tests use explicit test workers, never stand in for model accuracy."""
from dataclasses import replace
from pathlib import Path
import threading
import time

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.inference import PredictionError, window_starts
from app.main import create_app


class TestWorker:
    loaded = False
    def execute(self, path, progress):
        assert path.is_file()
        progress('decoding', .05)
        progress('extracting_features', .8)
        self.loaded = True
        return {'test_fixture_only': True}
    def close(self):
        pass


class InvalidWorker(TestWorker):
    def execute(self, path, progress):
        raise PredictionError('音频无法解码。')


@pytest.fixture
def settings(tmp_path):
    return Settings(tmp_path / 'mert', tmp_path / 'head.pt', tmp_path / 'uploads', max_upload_bytes=128)


def app_for(settings, worker=None, ready=True):
    return create_app(settings, worker or TestWorker(),
                      readiness=lambda s: (ready, None if ready else '缺少模型权重。'))


def wait_job(client, job):
    for _ in range(200):
        response = client.get('/api/jobs/' + job['job_id'], headers={'X-Job-Token': job['access_token']})
        assert response.status_code == 200
        if response.json()['status'] in ['completed', 'failed']:
            return response.json()
        time.sleep(.01)
    pytest.fail('Test job did not complete')


def test_window_contract():
    assert window_starts(24000) == [0]
    assert window_starts(1080000) == list(range(0, 840001, 120000))
    assert window_starts(1080024)[-1] == 840024
    with pytest.raises(PredictionError):
        window_starts(0)


def test_missing_model_is_not_fake_prediction(settings):
    with TestClient(app_for(settings, ready=False)) as c:
        health = c.get('/api/health').json()
        assert health['status'] == 'not_ready' and health['device'] == 'cpu'
        assert c.post('/api/jobs', files={'file': ('a.wav', b'a')}).status_code == 503
        assert not list(settings.upload_dir.iterdir())


def test_success_tokens_and_file_cleanup(settings):
    with TestClient(app_for(settings)) as c:
        r = c.post('/api/jobs', files={'file': ('../../unsafe.wav', b'audio')})
        assert r.status_code == 202
        job = r.json()
        assert len(job['access_token']) >= 32
        assert c.get('/api/jobs/' + job['job_id']).status_code == 404
        assert c.get('/api/jobs/' + job['job_id'], headers={'X-Job-Token': 'wrong'}).status_code == 404
        done = wait_job(c, job)
        assert done['status'] == 'completed' and done['progress'] == 1
        assert 'path' not in done and 'access_token' not in done
        assert done['result'] == {'test_fixture_only': True}
        assert not list(settings.upload_dir.iterdir())


def test_empty_oversize_format_cleanup(settings):
    with TestClient(app_for(settings)) as c:
        for name, content, expected in [('a.wav', b'', 400), ('a.wav', b'x' * 129, 413),
                                        ('a.exe', b'x', 415), ('a.m4a', b'x', 415)]:
            assert c.post('/api/jobs', files={'file': (name, content)}).status_code == expected
        assert not list(settings.upload_dir.iterdir())
        assert c.app.state.manager.reservations == 0


def test_request_limit_before_multipart(settings):
    with TestClient(app_for(settings)) as c:
        assert c.post('/api/jobs', content=b'x' * (300 * 1024), headers={'Content-Type': 'multipart/form-data; boundary=no'}).status_code == 413
        assert not list(settings.upload_dir.iterdir())


def test_failure_cleanup(settings):
    with TestClient(app_for(settings, InvalidWorker())) as c:
        job = c.post('/api/jobs', files={'file': ('a.wav', b'invalid')}).json()
        done = wait_job(c, job)
        assert done['status'] == 'failed'
        assert done['error'] == '音频无法解码。'
        assert not list(settings.upload_dir.iterdir())


def test_auth_and_cors(settings):
    settings = replace(settings, api_token='test-only-access-key')
    with TestClient(app_for(settings)) as c:
        assert c.post('/api/jobs', files={'file': ('a.wav', b'a')}).status_code == 401
        assert not list(settings.upload_dir.iterdir())
        assert c.post('/api/jobs', headers={'Authorization': 'Bearer test-only-access-key'}, files={'file': ('a.wav', b'a')}).status_code == 202
        r = c.options('/api/jobs', headers={'Origin': 'https://untrusted.invalid', 'Access-Control-Request-Method': 'POST'})
        assert 'access-control-allow-origin' not in r.headers


def test_queue_and_reservation_bounds(settings):
    release = threading.Event()
    class BlockingWorker(TestWorker):
        def execute(self, path, progress):
            release.wait(3)
            return {'test_fixture_only': True}
        def close(self):
            release.set()
    settings = replace(settings, max_queue_jobs=1)
    with TestClient(app_for(settings, BlockingWorker())) as c:
        first = c.post('/api/jobs', files={'file': ('a.wav', b'a')})
        assert first.status_code == 202
        # Wait until first task starts, then enqueue one and reject the next.
        for _ in range(100):
            if c.get('/api/health').json()['queue']['active']:
                break
            time.sleep(.01)
        assert c.post('/api/jobs', files={'file': ('b.wav', b'b')}).status_code == 202
        assert c.post('/api/jobs', files={'file': ('c.wav', b'c')}).status_code == 429
        release.set()
    assert not list(settings.upload_dir.iterdir())


def test_expired_result_removed(settings):
    settings = replace(settings, job_ttl_seconds=0)
    with TestClient(app_for(settings)) as c:
        job = c.post('/api/jobs', files={'file': ('a.wav', b'a')}).json()
        time.sleep(.08)
        assert c.get('/api/jobs/' + job['job_id'], headers={'X-Job-Token': job['access_token']}).status_code == 404
