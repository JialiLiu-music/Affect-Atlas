import type { Prediction, TimelinePoint } from './api'

export const windowFixtures: Array<TimelinePoint> = [
  { index: 0, start_seconds: 0, end_seconds: 10, center_seconds: 5, feature_bins: 7, valence: 1.23456789, arousal: -.25, display_valence: 1, display_arousal: -.25, out_of_range: true },
  { index: 1, start_seconds: 5, end_seconds: 15, center_seconds: 10, feature_bins: 8, valence: -.00001234, arousal: -1.4, display_valence: -.00001234, display_arousal: -1, out_of_range: true },
  { index: 2, start_seconds: 7, end_seconds: 17, center_seconds: 12, feature_bins: 8, valence: .4, arousal: .8, display_valence: .4, display_arousal: .8, out_of_range: false },
]
export const predictionFixture: Prediction = {
  valence: .123456789, arousal: -.23456789, display_valence: .123456789, display_arousal: -.23456789, out_of_range: false,
  duration_seconds: 17, feature_bins: 13, processing_seconds: 2, device: 'cpu', calibration: 'none', head_seed: 20261011, model_revision: 'test-fixture',
  timeline: { kind: 'exploratory_static_windows', window_seconds: 10, hop_seconds: 5, feature_context: 'reused_full_clip_mert_windows', validated_dynamic_model: false, smoothed: false, points: windowFixtures, disclaimer: 'Explicit test fixture, not model results.' },
}
