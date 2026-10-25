import { act, cleanup, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { MAX_POLL_MS } from './api'
import type { Health, Job } from './api'
import { useAnalysis } from './use-analysis'

const healthy: Health = { status: 'ready', device: 'cpu', model: { loaded: false, assets_available: true, reason: null, model_id: 'm-a-p/MERT-v1-95M', revision: 'test-revision', head_seed: 20261011 }, limits: { max_upload_bytes: 20971520, max_duration_seconds: 90, min_duration_seconds: 1, max_queue_jobs: 3, job_ttl_seconds: 3600 }, queue: { active: 0, queued: 0 }, prediction_task: 'overall_static_valence_arousal', calibration: 'none' }
const running: Job = { job_id: 'test-job', status: 'running', stage: 'extracting_features', progress: .3, result: null, error: null }
const audio = new File(['test-only bytes'], 'unit-test.wav', { type: 'audio/wav' })
const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
async function flush() { await act(async () => { await Promise.resolve(); await Promise.resolve() }) }
let fetchMock: ReturnType<typeof vi.fn>
beforeEach(() => { vi.useFakeTimers(); fetchMock = vi.fn(); vi.stubGlobal('fetch', fetchMock) })
afterEach(() => { cleanup(); vi.useRealTimers(); vi.unstubAllGlobals() })
function transport(jobRequest: () => Promise<Response> = async () => json(running), health: Health = healthy) {
  fetchMock.mockImplementation(async (url: string, options?: RequestInit) => {
    if (url.endsWith('/api/health')) return json(health)
    if (url.endsWith('/api/jobs') && options?.method === 'POST') return json({ job_id: 'test-job', access_token: 'test-only-token', status: 'queued' }, 202)
    return jobRequest()
  })
}
describe('analysis lifecycle', () => {
  it('blocks upload when model assets are missing', async () => {
    transport(undefined, { ...healthy, status: 'not_ready', model: { ...healthy.model, assets_available: false, reason: 'Missing assets' } })
    const { result } = renderHook(() => useAnalysis()); await flush()
    await act(async () => result.current.upload(audio))
    expect(fetchMock.mock.calls.some(call => call[1]?.method === 'POST')).toBe(false)
    expect(result.current.job).toBeNull()
  })
  it('polls every two seconds and authenticates only with a header', async () => {
    transport()
    const { result } = renderHook(() => useAnalysis()); await flush()
    await act(async () => result.current.upload(audio)); await flush()
    const count = () => fetchMock.mock.calls.filter(call => call[0].endsWith('/api/jobs/test-job')).length
    expect(count()).toBe(1)
    await act(async () => { await vi.advanceTimersByTimeAsync(1999) }); expect(count()).toBe(1)
    await act(async () => { await vi.advanceTimersByTimeAsync(1) }); expect(count()).toBe(2)
    const call = fetchMock.mock.calls.find(entry => entry[0].endsWith('/api/jobs/test-job'))
    expect(call?.[1].headers).toEqual({ 'X-Job-Token': 'test-only-token' })
    expect(call?.[0]).not.toContain('token')
    expect(localStorage.length).toBe(0)
  })
  it('prevents duplicate submission during a running task', async () => {
    transport(); const { result } = renderHook(() => useAnalysis()); await flush()
    await act(async () => result.current.upload(audio)); await flush()
    await act(async () => result.current.upload(audio))
    expect(fetchMock.mock.calls.filter(call => call[1]?.method === 'POST')).toHaveLength(1)
  })
  it('can resume after network errors without another upload', async () => {
    let failed = true
    transport(async () => { if (failed) throw new Error('Network unavailable'); return json(running) })
    const { result } = renderHook(() => useAnalysis()); await flush()
    await act(async () => result.current.upload(audio)); await flush()
    expect(result.current.paused).toBe(true)
    expect(result.current.error).toContain('Network unavailable')
    failed = false
    await act(async () => result.current.resume()); await flush()
    expect(result.current.paused).toBe(false)
    expect(result.current.job?.stage).toBe('extracting_features')
    expect(fetchMock.mock.calls.filter(call => call[1]?.method === 'POST')).toHaveLength(1)
  })
  it('stops polling at the twenty minute deadline even while paused', async () => {
    transport(async () => { throw new Error('offline') })
    const { result } = renderHook(() => useAnalysis()); await flush()
    await act(async () => result.current.upload(audio)); await flush()
    await act(async () => { await vi.advanceTimersByTimeAsync(MAX_POLL_MS) })
    expect(result.current.busy).toBe(false)
    expect(result.current.paused).toBe(false)
    expect(result.current.error).toContain('20 分钟')
    expect(fetchMock.mock.calls.filter(call => call[0].endsWith('/api/jobs/test-job'))).toHaveLength(1)
  })
  it('stops permanently on a failed terminal job and allows clearing the error', async () => {
    transport(async () => json({ ...running, status: 'failed', stage: 'failed', error: 'Decoder rejected audio' }))
    const { result } = renderHook(() => useAnalysis()); await flush()
    await act(async () => result.current.upload(audio)); await flush()
    expect(result.current.busy).toBe(false)
    expect(result.current.paused).toBe(false)
    expect(result.current.job?.status).toBe('failed')
    expect(result.current.error).toBe('Decoder rejected audio')
    await act(async () => { await vi.advanceTimersByTimeAsync(10000) })
    expect(fetchMock.mock.calls.filter(call => call[0].endsWith('/api/jobs/test-job'))).toHaveLength(1)
    await act(async () => result.current.clearResult())
    expect(result.current.job).toBeNull()
    expect(result.current.error).toBeNull()
  })
  it('aborts requests and clears every timer on unmount', async () => {
    transport(); const { result, unmount } = renderHook(() => useAnalysis()); await flush()
    await act(async () => result.current.upload(audio)); await flush()
    unmount()
    expect(vi.getTimerCount()).toBe(0)
  })
  it('finishes on real backend completion and stops future job requests', async () => {
    transport(async () => json({ ...running, status: 'completed', stage: 'completed', progress: 1, result: { valence: 1.7, arousal: -.2, display_valence: 1, display_arousal: -.2, out_of_range: true, duration_seconds: 3, feature_bins: 2, processing_seconds: 1, device: 'cpu', calibration: 'none', head_seed: 20261011, model_revision: 'fixture' } }))
    const { result } = renderHook(() => useAnalysis()); await flush()
    await act(async () => result.current.upload(audio)); await flush()
    expect(result.current.busy).toBe(false)
    expect(result.current.job?.result?.valence).toBe(1.7)
    await act(async () => { await vi.advanceTimersByTimeAsync(5000) })
    expect(fetchMock.mock.calls.filter(call => call[0].endsWith('/api/jobs/test-job'))).toHaveLength(1)
    await act(async () => result.current.clearResult())
    expect(result.current.job).toBeNull()
    expect(result.current.error).toBeNull()
  })
})
