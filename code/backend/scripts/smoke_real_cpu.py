"""Exercise real HTTP upload and real CPU MERT+trained-head inference.

Uses a locally generated test waveform, NOT an accuracy evaluation or a fake
model. No access token is written to the report. Uploaded server copies must
be deleted after each job. Run with the local backend already started.
"""
import argparse
import json
import math
from pathlib import Path
import time
import sys
import io

import httpx
import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import REVISION, HEAD_SHA256, Settings
from app.inference import file_sha


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='http://127.0.0.1:8000')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--durations', type=float, nargs='+', default=[3., 45.])
    parser.add_argument('--baseline-report', type=Path,
                        help='Optional prior execution report to verify unchanged overall outputs')
    args = parser.parse_args()
    settings = Settings.from_env()
    assert file_sha(settings.head_path) == HEAD_SHA256
    records = []
    headers = {'Authorization': 'Bearer ' + settings.api_token} if settings.api_token else {}
    with httpx.Client(base_url=args.base_url, timeout=30, headers=headers) as client:
        before = client.get('/api/health')
        before.raise_for_status()
        assert before.json()['status'] == 'ready' and before.json()['device'] == 'cpu'
        for duration in args.durations:
            sr = 24000
            t = np.arange(round(duration * sr), dtype=np.float32) / sr
            wave = (.08 * np.sin(2 * np.pi * 220 * t) + .04 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
            audio = io.BytesIO()
            sf.write(audio, wave, sr, format='WAV', subtype='PCM_16')
            started = time.perf_counter()
            response = client.post('/api/jobs', files={'file': ('generated-test.wav', audio.getvalue(), 'audio/wav')})
            assert response.status_code == 202, response.text
            ticket = response.json()
            request_headers = {'X-Job-Token': ticket['access_token']}
            last_stage = None
            stages = []
            deadline = time.monotonic() + 1200
            while time.monotonic() < deadline:
                poll = client.get('/api/jobs/' + ticket['job_id'], headers=request_headers)
                poll.raise_for_status()
                job = poll.json()
                if job['stage'] != last_stage:
                    last_stage = job['stage']
                    stages.append(last_stage)
                    print('TASK_STAGE', duration, last_stage, job['progress'], flush=True)
                if job['status'] == 'failed':
                    raise RuntimeError(job['error'])
                if job['status'] == 'completed':
                    break
                time.sleep(.5)
            else:
                raise TimeoutError('Real CPU inference did not complete')
            result = job['result']
            assert result['device'] == 'cpu' and result['model_revision'] == REVISION
            assert result['head_seed'] == 20261011 and result['calibration'] == 'none'
            assert all(math.isfinite(result[axis]) for axis in ['valence', 'arousal'])
            assert abs(result['duration_seconds'] - duration) <= .0001
            assert result['feature_bins'] == math.floor(duration - .5) + 1
            from app.timeline import segments
            timeline = result['timeline']
            assert timeline['kind'] == 'exploratory_static_windows'
            assert timeline['validated_dynamic_model'] is False and timeline['smoothed'] is False
            assert len(timeline['points']) == len(segments(duration))
            assert timeline['points'][0]['start_seconds'] == 0
            assert abs(timeline['points'][-1]['end_seconds'] - duration) < 1e-6
            for point in timeline['points']:
                assert all(math.isfinite(point[k]) for k in ['valence', 'arousal'])
            if duration <= 10:
                assert len(timeline['points']) == 1
                assert max(abs(timeline['points'][0][k] - result[k]) for k in ['valence', 'arousal']) < 1e-6
            if args.baseline_report:
                prior = json.loads(args.baseline_report.read_text(encoding='utf-8'))
                matches = [r for r in prior['tests'] if r['duration_seconds'] == duration]
                for baseline in matches:
                    assert max(abs(result[k] - baseline['result'][k]) for k in ['valence', 'arousal']) < 1e-6
            assert not list(settings.upload_dir.glob('mer-upload-*.audio')), 'Server retained uploaded audio'
            records.append({'input': 'generated two-frequency test waveform; not musical accuracy evidence',
                            'duration_seconds': duration, 'stages_observed': stages,
                            'http_wall_seconds': round(time.perf_counter() - started, 3), 'result': result})
            print('REAL_CPU_TASK_COMPLETED', duration, 'seconds', result['processing_seconds'], flush=True)
        after = client.get('/api/health').json()
        assert after['model']['loaded'] is True
    report = {'status': 'REAL_CPU_UPLOAD_INFERENCE_PASS', 'device': 'cpu',
              'head_sha256': HEAD_SHA256, 'model_revision': REVISION,
              'tests': records, 'health_after': after,
              'scope': 'Real model execution through HTTP using generated audio, not emotion accuracy or representative performance benchmark'}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('REAL_CPU_UPLOAD_INFERENCE_PASS', flush=True)


if __name__ == '__main__':
    main()
