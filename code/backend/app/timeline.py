"""Exploratory static-head scores over already extracted full-clip features.

The MERT context is reused, not re-extracted per local audio crop. This is not
an independently trained/validated dynamic emotion model or second-level truth.
"""
import math
import numpy as np

WINDOW_SECONDS = 10.0
HOP_SECONDS = 5.0
DISCLAIMER = ('探索性窗口评分：静态整体评分模型作用于固定10秒窗口、5秒步长的时间特征；'
              '复用整段MERT上下文，窗口短于45秒训练片段，局部准确性尚未验证；'
              '非逐秒情绪真值或已验证动态模型。曲线未平滑、未校正。')


def segments(duration: float):
    if not math.isfinite(duration) or duration < 1 or duration > 90 + 1e-8:
        raise ValueError('Invalid duration for timeline')
    if duration <= WINDOW_SECONDS:
        return [(0.0, duration)]
    last = duration - WINDOW_SECONDS
    starts = [i * HOP_SECONDS for i in range(math.floor(last / HOP_SECONDS) + 1)]
    if not math.isclose(starts[-1], last, abs_tol=1e-9, rel_tol=0):
        starts.append(last)
    return [(start, min(start + WINDOW_SECONDS, duration)) for start in starts]


def timeline_scores(features: np.ndarray, duration: float, predict_pooled):
    windows = segments(duration)
    if features.ndim != 2 or features.shape != (math.floor(duration - .5) + 1, 768):
        raise ValueError('Unexpected feature contract')
    if not np.isfinite(features).all():
        raise ValueError('Nonfinite timeline features')
    centers = np.arange(len(features), dtype=np.float64) + .5
    points = []
    for index, (start, end) in enumerate(windows):
        # Include a final partial bin whose center lies exactly at clip end.
        # Ordinary adjacent window endpoint bins remain half-open.
        last = math.isclose(end, duration, abs_tol=1e-9, rel_tol=0)
        mask = (centers >= start) & ((centers < end) | (last & (centers <= end)))
        selected = features[mask]
        if not len(selected):
            raise ValueError('No valid feature bins for window')
        pooled = selected.mean(axis=0, dtype=np.float32)
        prediction = np.asarray(predict_pooled(pooled), dtype=np.float64)
        if prediction.shape != (2,) or not np.isfinite(prediction).all():
            raise ValueError('Invalid window prediction')
        v, a = [float(x) for x in prediction]
        points.append(dict(index=index, start_seconds=round(start, 6), end_seconds=round(end, 6),
                           center_seconds=round((start + end) / 2, 6), feature_bins=len(selected),
                           valence=v, arousal=a, display_valence=max(-1., min(1., v)),
                           display_arousal=max(-1., min(1., a)), out_of_range=abs(v) > 1 or abs(a) > 1))
    return dict(kind='exploratory_static_windows', window_seconds=WINDOW_SECONDS,
                hop_seconds=HOP_SECONDS, feature_context='reused_full_clip_mert_windows',
                validated_dynamic_model=False, smoothed=False, points=points, disclaimer=DISCLAIMER)
