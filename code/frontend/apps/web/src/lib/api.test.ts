import { afterEach, describe, expect, it, vi } from 'vitest'
import { jobHeaders, plotCoordinate, request, uploadHeaders, uploadProblem } from './api'

afterEach(() => { vi.unstubAllGlobals(); vi.unstubAllEnvs() })
describe('upload constraints', () => {
  it('accepts the exact 20 MiB boundary', () => expect(uploadProblem({ size: 20971520 })).toBeNull())
  it('rejects oversized and empty input', () => { expect(uploadProblem({ size: 20971521 })).toContain('20 MB'); expect(uploadProblem({ size: 0 })).toContain('为空') })
  it('requires M4A conversion instead of advertising support', () => expect(uploadProblem({ size: 128, name: 'music.M4A' })).toContain('请先转换'))
  it('respects limits from health', () => expect(uploadProblem({ size: 1025 }, 1024)).not.toBeNull())
})
describe('coordinate display', () => {
  it('clips only visual coordinates', () => { expect(plotCoordinate(1.75)).toBe(1); expect(plotCoordinate(-2.5)).toBe(-1); expect(plotCoordinate(.25)).toBe(.25) })
})
describe('API transport', () => {
  it('preserves the backend detail message', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: '缺少真实模型资产' }), { status: 503 })))
    await expect(request('/api/health', new AbortController().signal)).rejects.toThrow('缺少真实模型资产')
  })
  it('reports HTTP code when response cannot be decoded', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('upstream error', { status: 502 })))
    await expect(request('/api/health', new AbortController().signal)).rejects.toThrow('HTTP 502')
  })
  it('puts the job token exclusively in a header', () => expect(jobHeaders({ job_id: 'job-1', access_token: 'test-token', status: 'queued' })).toEqual({ 'X-Job-Token': 'test-token' }))
  it('supports an optional upload Bearer token', () => { vi.stubEnv('VITE_API_AUTH_TOKEN', 'local-demo'); expect(uploadHeaders()).toEqual({ Authorization: 'Bearer local-demo' }) })
  it('adds the configured Bearer token to job queries too', () => { vi.stubEnv('VITE_API_AUTH_TOKEN', 'local-demo'); expect(jobHeaders({ job_id: 'job-1', access_token: 'test-token', status: 'queued' })).toEqual({ Authorization: 'Bearer local-demo', 'X-Job-Token': 'test-token' }) })
  it('does not add authorization when unconfigured', () => { vi.stubEnv('VITE_API_AUTH_TOKEN', ''); expect(uploadHeaders()).toEqual({}) })
})
