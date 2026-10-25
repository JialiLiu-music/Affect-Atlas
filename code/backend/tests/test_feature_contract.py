"""Numerical feature-contract checks with an explicit small test double.

These tests compare the demo against the original extraction function, not
against real MERT audio predictions. No test model is exposed by the API.
"""
import ast
from pathlib import Path
from types import SimpleNamespace
import contextlib
import math
import sys

import numpy as np
import pytest

from app.config import Settings
from app.inference import CpuPredictor


class Tensor:
    def __init__(self, array):
        self.array = np.asarray(array)
    def to(self, _): return self
    def float(self): return Tensor(self.array.astype(np.float32))
    def cpu(self): return self
    def numpy(self): return self.array
    def mean(self, axis=None, dim=None): return Tensor(self.array.mean(axis if dim is None else dim))
    def __getitem__(self, key): return Tensor(self.array[key])


@pytest.mark.parametrize('size', [24000, 168012, 1080000, 1080031])
def test_feature_contract_matches_original(monkeypatch, tmp_path, size):
    original_path = Path(__file__).resolve().parents[4] / 'Musik' / 'extract_mert.py'
    if not original_path.is_file():
        pytest.skip('Original workspace extractor unavailable in standalone checkout')
    module = ast.parse(original_path.read_text(encoding='utf-8'))
    names = ['iter_windows', 'layer_average', 'extract_track']
    functions = ast.Module(body=[node for node in module.body if isinstance(node, ast.FunctionDef) and node.name in names], type_ignores=[])
    torch = SimpleNamespace(stack=lambda rows, dim=0: Tensor(np.stack([r.array for r in rows], axis=dim)),
                            from_numpy=lambda x: Tensor(x),
                            inference_mode=contextlib.nullcontext,
                            nn=SimpleNamespace(Module=object), Tensor=Tensor,
                            device=lambda x: x)
    monkeypatch.setitem(sys.modules, 'torch', torch)
    wave = np.sin(np.arange(size) / 100.).astype(np.float32)
    calls = []
    def model(values, output_hidden_states):
        calls.append(len(values.array))
        # Deterministic frame values exercise layer/window/bin averaging.
        base = np.arange(500 * 768, dtype=np.float32).reshape(1, 500, 768) / 100000.
        base += float(values.array.mean())
        return SimpleNamespace(hidden_states=tuple(Tensor(base + i) for i in range(6)))
    def extractor(window, **kwargs):
        return SimpleNamespace(input_values=Tensor(window))
    scope = dict(np=np, torch=torch, math=math, TARGET_SAMPLE_RATE=24000, FEATURE_DIM=768,
                 Wav2Vec2FeatureExtractor=object)
    exec(compile(functions, str(original_path), 'exec'), scope)
    expected, times = scope['extract_track'](model, extractor, wave, 'cpu', 10., 5., 1.)
    original_calls = len(calls)
    settings = Settings(tmp_path/'mert', tmp_path/'head', tmp_path/'uploads')
    predictor = CpuPredictor(settings)
    predictor.model = model
    predictor.extractor = extractor
    predictor.load = lambda: None
    predictor.head = lambda pooled: Tensor(np.array([pooled.array[0], pooled.array[-1]], dtype=np.float32))
    monkeypatch.setattr('app.inference.decode_audio', lambda p, s: wave)
    stages = []
    result = predictor.predict(tmp_path/'fixture.audio', lambda s, p: stages.append((s, p)))
    expected_prediction = expected.mean(0)[[0, -1]]
    np.testing.assert_allclose([result['valence'], result['arousal']], expected_prediction, rtol=0, atol=1e-6)
    assert result['feature_bins'] == len(times)
    assert result['duration_seconds'] == round(size / 24000, 4)
    assert result['device'] == 'cpu' and result['calibration'] == 'none'
    assert set(calls) == {240000}  # ten-second windows, including padding
    assert stages[-1][0] == 'predicting'
    assert len(calls) == 2 * original_calls  # no additional MERT passes for timeline
    assert result['timeline']['validated_dynamic_model'] is False
    assert result['timeline']['points']
