import { useCallback, useEffect, useRef, useState } from 'react'
import { MAX_POLL_MS, POLL_INTERVAL_MS, errorMessage, jobHeaders, request, uploadHeaders, uploadProblem } from './api'
import type { Health, Job, Ticket } from './api'

export function useAnalysis() {
  const [health, setHealth] = useState<Health | null>(null)
  const [healthError, setHealthError] = useState<string | null>(null)
  const [healthChecking, setHealthChecking] = useState(false)
  const [healthRefresh, setHealthRefresh] = useState(0)
  const [job, setJob] = useState<Job | null>(null)
  const [busy, setBusy] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [paused, setPaused] = useState(false)
  const ticket = useRef<Ticket | null>(null)
  const deadline = useRef(0)
  const controller = useRef<AbortController | null>(null)
  const next = useRef<ReturnType<typeof setTimeout> | null>(null)
  const stopTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const mounted = useRef(true)
  const submission = useRef(false)
  const stop = useCallback(() => {
    controller.current?.abort()
    controller.current = null
    if (next.current) clearTimeout(next.current)
    if (stopTimer.current) clearTimeout(stopTimer.current)
    next.current = null
    stopTimer.current = null
  }, [])
  useEffect(() => {
    mounted.current = true
    return () => { mounted.current = false; stop(); ticket.current = null }
  }, [stop])
  useEffect(() => {
    let disposed = false
    let timer: ReturnType<typeof setTimeout> | undefined
    let active: AbortController | undefined
    const check = async () => {
      active = new AbortController()
      setHealthChecking(true)
      const timeout = setTimeout(() => active?.abort(), 15000)
      try {
        const value = await request<Health>('/api/health', active.signal)
        if (!disposed) { setHealth(value); setHealthError(null) }
      } catch (err) {
        if (!disposed) { setHealth(null); setHealthError(active.signal.aborted ? '健康检查超时（15 秒），请确认后端正在运行。' : errorMessage(err)) }
      } finally {
        clearTimeout(timeout)
        if (!disposed) { setHealthChecking(false); timer = setTimeout(check, 5000) }
      }
    }
    void check()
    return () => { disposed = true; active?.abort(); clearTimeout(timer) }
  }, [healthRefresh])
  const poll = useCallback(() => {
    stop()
    const current = ticket.current
    if (!current || !mounted.current) return
    if (Date.now() >= deadline.current) { setError('已达到 20 分钟轮询上限，已停止查询。后端任务可能仍在处理；请检查后端后再决定是否重新上传。'); setBusy(false); setPaused(false); return }
    const active = new AbortController()
    controller.current = active
    setBusy(true)
    setPaused(false)
    setError(null)
    stopTimer.current = setTimeout(() => {
      active.abort()
      if (next.current) clearTimeout(next.current)
      if (mounted.current) { setError('已达到 20 分钟轮询上限，已停止查询。后端任务可能仍在处理，请检查后端。'); setBusy(false); setPaused(false) }
    }, deadline.current - Date.now())
    const check = async () => {
      const perRequest = new AbortController()
      const abort = () => perRequest.abort()
      active.signal.addEventListener('abort', abort, { once: true })
      const timeout = setTimeout(abort, 15000)
      try {
        const value = await request<Job>(`/api/jobs/${encodeURIComponent(current.job_id)}`, perRequest.signal, { headers: jobHeaders(current) })
        if (active.signal.aborted || !mounted.current) return
        setJob(value)
        if (value.status === 'completed' || value.status === 'failed') {
          setBusy(false)
          setError(value.status === 'failed' ? value.error || '后端任务失败，未生成预测。' : null)
          stop()
          ticket.current = null
        } else next.current = setTimeout(check, POLL_INTERVAL_MS)
      } catch (err) {
        if (active.signal.aborted || !mounted.current) return
        setPaused(true)
        setError(`状态查询中断：${perRequest.signal.aborted ? '请求超时（15 秒）' : errorMessage(err)}。可恢复查询，无需重复上传。`)
        // Keep the overall deadline running while paused.
      } finally {
        clearTimeout(timeout)
        active.signal.removeEventListener('abort', abort)
      }
    }
    void check()
  }, [stop])
  const upload = useCallback(async (file: File) => {
    if (submission.current || busy || healthError || health?.status !== 'ready' || !health.model.assets_available) return
    const problem = uploadProblem(file, health.limits.max_upload_bytes)
    if (problem) { setError(problem); return }
    submission.current = true
    stop()
    ticket.current = null
    setJob(null)
    setError(null)
    setPaused(false)
    setBusy(true)
    setUploading(true)
    const active = new AbortController()
    controller.current = active
    const timeout = setTimeout(() => active.abort(), 60000)
    const body = new FormData()
    body.append('file', file)
    try {
      const value = await request<Ticket>('/api/jobs', active.signal, { method: 'POST', body, headers: uploadHeaders() })
      if (!mounted.current || controller.current !== active) return
      ticket.current = value
      deadline.current = Date.now() + MAX_POLL_MS
      setJob({ job_id: value.job_id, status: 'queued', stage: 'queued', progress: 0, result: null, error: null })
      setUploading(false)
      poll()
    } catch (err) {
      if (!mounted.current) return
      setError(active.signal.aborted ? '上传超时，未确认任务是否创建。请先检查后端任务，避免重复上传。' : `上传失败：${errorMessage(err)}`)
      setBusy(false)
      setUploading(false)
    } finally { clearTimeout(timeout); submission.current = false }
  }, [busy, health, healthError, poll, stop])
  const clearResult = useCallback(() => {
    if (busy || submission.current) return
    stop()
    ticket.current = null
    setJob(null)
    setError(null)
    setPaused(false)
  }, [busy, stop])
  return { health, healthError, healthChecking, refreshHealth: () => setHealthRefresh(value => value + 1), job, busy, uploading, error, paused, resume: poll, upload, clearResult }
}
