import type { Prediction, TimelinePoint } from './api'

export function formatScore(value: number): string { return value.toFixed(4) }
export function formatSeconds(value: number): string { return `${value.toFixed(2)} s` }
export function formatDelta(value: number, overall: number): string {
  const delta = value - overall
  return `${delta > 0 ? '+' : ''}${formatScore(delta)}`
}
// Overlapping windows: prefer a containing window, then the nearest center; ties keep source order.
export function nearestWindow(points: Array<TimelinePoint>, time: number): TimelinePoint | null {
  const containing = points.filter(point => time >= point.start_seconds && time <= point.end_seconds)
  return (containing.length ? containing : points).reduce<TimelinePoint | null>((best, point) =>
    !best || Math.abs(point.center_seconds - time) < Math.abs(best.center_seconds - time) ? point : best, null)
}
export function scoreDomain(points: Array<TimelinePoint>): [number, number] {
  return [Math.min(-1, ...points.flatMap(point => [point.valence, point.arousal])), Math.max(1, ...points.flatMap(point => [point.valence, point.arousal]))]
}
export function predictionJson(prediction: Prediction): string { return JSON.stringify(prediction, null, 2) }
export function timelineCsv(points: Array<TimelinePoint>): string {
  const rows = points.map(point => [point.start_seconds, point.end_seconds, point.center_seconds, point.feature_bins, point.valence, point.arousal].map(value => Number.isFinite(value) ? String(value) : '').join(','))
  return '\uFEFFstart,end,center,bins,valence,arousal\r\n' + rows.join('\r\n') + '\r\n'
}
export function downloadPrediction(prediction: Prediction, format: 'json' | 'csv'): void {
  const body = format === 'json' ? predictionJson(prediction) : timelineCsv(prediction.timeline?.points ?? [])
  const url = URL.createObjectURL(new Blob([body], { type: format === 'json' ? 'application/json;charset=utf-8' : 'text/csv;charset=utf-8' }))
  const link = document.createElement('a')
  link.href = url
  link.download = format === 'json' ? 'music-affect-prediction.json' : 'music-affect-windows.csv'
  document.body.append(link)
  try { link.click() } finally { link.remove(); URL.revokeObjectURL(url) }
}
