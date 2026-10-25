"""Window scores are explicit static predictions, with honest time/context metadata."""
import math
import numpy as np
import pytest
from app.timeline import segments, timeline_scores


@pytest.mark.parametrize('duration,count', [(1., 1), (1.5, 1), (3., 1), (10., 1),
                                           (10.001, 2), (15., 2), (15.1, 3),
                                           (45., 8), (52.35, 10), (90., 17)])
def test_windows_cover_duration_and_include_tail(duration, count):
    windows = segments(duration)
    assert len(windows) == count
    assert windows[0][0] == 0
    assert abs(windows[-1][1] - duration) < 1e-8
    assert len({round(a, 9) for a, _ in windows}) == count
    for start, end in windows:
        assert 0 <= start < end <= duration
        assert end - start <= 10 + 1e-8
    assert all(b <= previous_end for (_, previous_end), (b, _) in zip(windows, windows[1:]))


def test_one_short_clip_uses_all_bins_including_endpoint():
    x = np.zeros((2, 768), dtype=np.float32)
    x[0, :2] = [.2, .4]
    x[1, :2] = [.6, .8]
    result = timeline_scores(x, 1.5, lambda z: z[:2])
    point = result['points'][0]
    np.testing.assert_allclose([point['valence'], point['arousal']], x.mean(0)[:2])
    assert point['feature_bins'] == 2
    assert point['start_seconds'] == 0 and point['end_seconds'] == 1.5


def test_half_open_bins_fixed_hop_and_actual_head_output():
    x = np.zeros((20, 768), dtype=np.float32)
    x[:, 0] = np.arange(20)
    x[:, 1] = -np.arange(20)
    result = timeline_scores(x, 20., lambda z: z[:2])
    points = result['points']
    assert [p['start_seconds'] for p in points] == [0, 5, 10]
    assert [p['center_seconds'] for p in points] == [5, 10, 15]
    assert [p['valence'] for p in points] == [4.5, 9.5, 14.5]
    assert [p['feature_bins'] for p in points] == [10, 10, 10]
    assert all(p['display_valence'] == 1 and p['out_of_range'] for p in points)
    assert result['validated_dynamic_model'] is False and result['smoothed'] is False
    assert result['feature_context'] == 'reused_full_clip_mert_windows'
    assert '非逐秒' in result['disclaimer']


@pytest.mark.parametrize('duration', [0, float('nan'), float('inf'), 91])
def test_invalid_duration_rejected(duration):
    with pytest.raises(ValueError): segments(duration)


def test_invalid_features_or_prediction_rejected():
    with pytest.raises(ValueError): timeline_scores(np.zeros((3, 4)), 3, lambda _: [0, 0])
    with pytest.raises(ValueError): timeline_scores(np.full((3, 768), np.nan), 3, lambda _: [0, 0])
    with pytest.raises(ValueError): timeline_scores(np.zeros((3, 768)), 3, lambda _: [float('nan'), 0])
