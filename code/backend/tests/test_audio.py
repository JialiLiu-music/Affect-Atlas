"""Real PCM audio tests, independent of missing MERT/head assets."""
from dataclasses import replace
import numpy as np
import pytest
import soundfile as sf

from app.config import Settings
from app.inference import PredictionError, decode_audio


@pytest.fixture
def settings(tmp_path):
    return Settings(tmp_path/'mert', tmp_path/'head.pt', tmp_path/'uploads')


def test_complete_mono_and_same_sample_rate(settings, tmp_path):
    sr = 24000
    wave = np.sin(2 * np.pi * 440 * np.arange(sr * 2) / sr).astype(np.float32) * .1
    path = tmp_path/'valid.audio'
    sf.write(path, wave, sr, format='WAV', subtype='FLOAT')
    decoded = decode_audio(path, settings)
    np.testing.assert_array_equal(decoded, wave)
    assert len(decoded) == 48000


def test_full_stereo_mean_and_resampling(settings, tmp_path):
    sr = 48000
    wave = np.stack([np.ones(sr * 2) * .1, np.ones(sr * 2) * .3], axis=1).astype(np.float32)
    path = tmp_path/'valid.audio'
    sf.write(path, wave, sr, format='WAV', subtype='FLOAT')
    decoded = decode_audio(path, settings)
    assert len(decoded) == 48000 and np.isfinite(decoded).all()
    assert abs(float(decoded[100:-100].mean()) - .2) < 1e-5


def test_duration_not_silently_truncated(settings, tmp_path):
    path = tmp_path/'long.audio'
    sf.write(path, np.zeros(24000 * 3, dtype=np.float32), 24000, format='WAV')
    with pytest.raises(PredictionError, match='不会自动截断'):
        decode_audio(path, replace(settings, max_duration_seconds=2))
    sf.write(path, np.zeros(12000, dtype=np.float32), 24000, format='WAV')
    with pytest.raises(PredictionError):
        decode_audio(path, settings)


def test_invalid_file_and_nonfinite(settings, tmp_path):
    path = tmp_path/'invalid.audio'
    path.write_bytes(b'this is not an audio file')
    with pytest.raises(PredictionError, match='无法解码'):
        decode_audio(path, settings)
    sf.write(path, np.full(24000, np.nan, dtype=np.float32), 24000, format='WAV', subtype='FLOAT')
    with pytest.raises(PredictionError, match='非有限'):
        decode_audio(path, settings)
