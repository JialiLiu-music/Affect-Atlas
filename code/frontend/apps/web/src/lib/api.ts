export interface Health {
  status: 'ready' | 'not_ready'
  device: 'cpu'
  model: { loaded: boolean; assets_available: boolean; reason: string | null; model_id: string; revision: string; head_seed: number }
  limits: { max_upload_bytes: number; max_duration_seconds: number; min_duration_seconds: number; max_queue_jobs: number; job_ttl_seconds: number }
  queue: { active: number; queued: number }
  prediction_task: 'overall_static_valence_arousal'
  calibration: 'none'
}
export interface TimelinePoint {
  index: number; start_seconds: number; end_seconds: number; center_seconds: number; feature_bins: number
  valence: number; arousal: number; display_valence: number; display_arousal: number; out_of_range: boolean
}
export interface PredictionTimeline {
  kind: 'exploratory_static_windows'; window_seconds: 10; hop_seconds: 5
  feature_context: 'reused_full_clip_mert_windows'; validated_dynamic_model: false; smoothed: false
  points: Array<TimelinePoint>; disclaimer: string
}
export interface Prediction {
  timeline?: PredictionTimeline
  valence: number; arousal: number; display_valence: number; display_arousal: number
  out_of_range: boolean; duration_seconds: number; feature_bins: number; processing_seconds: number
  device: 'cpu'; calibration: 'none'; head_seed: number; model_revision: string
}
export interface Job {
  job_id: string
  status: 'queued' | 'running' | 'completed' | 'failed'
  stage: 'queued' | 'decoding' | 'loading_model' | 'extracting_features' | 'predicting' | 'completed' | 'failed'
  progress: number
  result: Prediction | null
  error: string | null
}
export interface Ticket { job_id: string; access_token: string; status: 'queued' }
export const API_BASE = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/+$/, '')
export const MAX_POLL_MS = 20 * 60 * 1000
export const POLL_INTERVAL_MS = 2000
export const stages: Record<Job['stage'], string> = { queued: '等待 CPU 工作队列', decoding: '解码与检查音频', loading_model: '加载模型', extracting_features: '提取音乐特征', predicting: '计算整体情绪数值', completed: '分析完成', failed: '分析失败' }
export function uploadProblem(file: { size: number; name?: string }, maxBytes = 20971520): string | null {
  if (file.name && /\.m4a$/i.test(file.name)) return 'M4A 暂不支持，请先转换为 WAV、MP3、FLAC 或 OGG。'
  if (!file.size) return '音频文件为空，请重新选择。'
  if (file.size > maxBytes) return `文件超过 ${(maxBytes / 1024 / 1024).toFixed(0)} MB 上限，请选择较小的音频。`
  return null
}
export function plotCoordinate(value: number): number { return Math.max(-1, Math.min(1, value)) }
export async function request<T>(path: string, signal: AbortSignal, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, { ...init, signal })
  if (!response.ok) {
    let detail = `HTTP ${response.status}`
    try { const body: unknown = await response.json(); if (body && typeof body === 'object' && 'detail' in body && typeof body.detail === 'string') detail = body.detail } catch { /* Preserve HTTP status when response is not JSON. */ }
    throw new Error(detail)
  }
  return response.json() as Promise<T>
}
export function errorMessage(error: unknown): string { return error instanceof Error ? error.message : String(error) }
export function jobHeaders(ticket: Ticket): HeadersInit { return { ...uploadHeaders(), 'X-Job-Token': ticket.access_token } }
export function uploadHeaders(): Record<string, string> {
  const token = import.meta.env.VITE_API_AUTH_TOKEN?.trim()
  return token ? { Authorization: `Bearer ${token}` } : {}
}
