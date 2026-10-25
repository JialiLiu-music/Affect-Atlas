import { createFileRoute } from '@tanstack/react-router'
import { useEffect, useState } from 'react'
import { Activity, ArrowUpRight, AudioLines, CheckCircle2, Cpu, FileAudio, FlaskConical, Info, LoaderCircle, RefreshCw, ShieldCheck, UploadCloud } from 'lucide-react'
import { Alert, AlertDescription, AlertTitle } from '@workspace/ui/components/alert'
import { Badge } from '@workspace/ui/components/badge'
import { Button } from '@workspace/ui/components/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@workspace/ui/components/card'
import { Input } from '@workspace/ui/components/input'
import { Label } from '@workspace/ui/components/label'
import { Progress } from '@workspace/ui/components/progress'
import { Separator } from '@workspace/ui/components/separator'
import { plotCoordinate, stages, uploadProblem } from '@/lib/api'
import type { Prediction } from '@/lib/api'
import { TimelinePanel } from '@/components/timeline-panel'
import { formatScore } from '@/lib/timeline'
import { useAnalysis } from '@/lib/use-analysis'
import { useTimelinePlayer } from '@/lib/use-timeline-player'

export const Route = createFileRoute('/')({ component: AnalysisPage })

function EmotionPlane({ result }: { result: Prediction | null }) {
  const x = result ? 70 + (plotCoordinate(result.display_valence) + 1) * 145 : 0
  const y = result ? 330 - (plotCoordinate(result.display_arousal) + 1) * 145 : 0
  return <svg viewBox="0 0 430 415" role="img" aria-label={result ? `整体情绪坐标：愉悦度 ${result.valence}，唤醒度 ${result.arousal}` : '尚无预测。横轴愉悦度、纵轴唤醒度，范围均为负一到正一。'} className="emotion-plane">
    <defs><linearGradient id="plane-gradient" x1="0" y1="1" x2="1" y2="0"><stop offset="0" stopColor="#f8fafc"/><stop offset="1" stopColor="#f2efff"/></linearGradient></defs>
    <rect x="70" y="40" width="290" height="290" rx="14" fill="url(#plane-gradient)"/>
    {[-1, -.5, 0, .5, 1].map(value => <g key={value}>
      <line x1={70 + (value + 1) * 145} y1="40" x2={70 + (value + 1) * 145} y2="330" stroke={value === 0 ? '#9ca5bb' : '#e1e5ef'} strokeDasharray={value === 0 ? undefined : '3 5'}/>
      <line x1="70" y1={330 - (value + 1) * 145} x2="360" y2={330 - (value + 1) * 145} stroke={value === 0 ? '#9ca5bb' : '#e1e5ef'} strokeDasharray={value === 0 ? undefined : '3 5'}/>
      <text x={70 + (value + 1) * 145} y="352" textAnchor="middle" className="tick">{value}</text>
      <text x="55" y={335 - (value + 1) * 145} textAnchor="end" className="tick">{value}</text>
    </g>)}
    <text x="89" y="66" className="quadrant">消极 · 激动方向</text><text x="252" y="66" className="quadrant">积极 · 激动方向</text>
    <text x="89" y="314" className="quadrant">消极 · 平静方向</text><text x="252" y="314" className="quadrant">积极 · 平静方向</text>
    <text x="215" y="386" textAnchor="middle" className="axis">愉悦度 Valence →</text>
    <text x="17" y="185" textAnchor="middle" transform="rotate(-90 17 185)" className="axis">唤醒度 Arousal →</text>
    {result && <g><circle cx={x} cy={y} r="15" fill="#7657d6" opacity=".13"/><circle cx={x} cy={y} r="7" fill="#7657d6" stroke="white" strokeWidth="3"/><title>愉悦度 {result.valence}，唤醒度 {result.arousal}</title></g>}
    {!result && <g><rect x="136" y="166" width="158" height="38" rx="19" fill="white" stroke="#e3e6ef"/><text x="215" y="190" textAnchor="middle" className="axis">等待真实分析结果</text></g>}
  </svg>
}

function AnalysisPage() {
  const analysis = useAnalysis()
  const player = useTimelinePlayer()
  const { health, healthError, healthChecking, job, busy, uploading, error, paused } = analysis
  const [file, setFile] = useState<File | null>(null)
  const [audioUrl, setAudioUrl] = useState<string | null>(null)
  const [localError, setLocalError] = useState<string | null>(null)
  useEffect(() => {
    if (!file) { setAudioUrl(null); return }
    const url = URL.createObjectURL(file)
    setAudioUrl(url)
    return () => URL.revokeObjectURL(url)
  }, [file])
  const ready = health?.status === 'ready' && health.model.assets_available && !healthError
  const result = job?.status === 'completed' ? job.result : null
  const problem = file ? uploadProblem(file, health?.limits.max_upload_bytes) : null
  const maxBytes = health?.limits.max_upload_bytes ?? 20971520
  const maxDuration = health?.limits.max_duration_seconds ?? 90
  const minDuration = health?.limits.min_duration_seconds ?? 1
  const select = (selected: File | undefined) => {
    if (busy) return
    analysis.clearResult()
    player.reset()
    setFile(selected ?? null)
    setLocalError(selected ? uploadProblem(selected, maxBytes) : null)
  }
  return <div className="app-shell">
    <header className="site-header"><div className="header-inner">
      <div className="brand"><div className="brand-symbol"><AudioLines size={22}/></div><div><strong>音乐情绪实验室</strong><span>MUSIC AFFECT · RESEARCH DEMO</span></div></div>
      <Badge variant="outline" className="research-badge"><FlaskConical size={13}/> 科研演示</Badge>
    </div></header>
    <main className="main-content">
      <section className="intro" aria-labelledby="page-title">
        <div className="eyebrow"><span/> 整体音乐情绪 · CPU 推理</div>
        <h1 id="page-title">听见音乐，<span>观察情绪。</span></h1>
        <p>上传一段音乐，观察模型输出的整体愉悦度与唤醒度。<br className="desktop-break"/>一个二维视角，探索音乐的情绪表达，而不是给感受下定义。</p>
        <div className="intro-tags"><span><Cpu size={15}/> 仅 CPU 计算</span><span><ShieldCheck size={15}/> 音频临时处理</span><span><Activity size={15}/> 非实时轨迹</span></div>
      </section>
      <div className="workspace-grid">
        <section className="input-column" aria-label="上传与分析状态">
          <Card className="panel status-panel"><CardContent>
            <div className="status-heading"><div className="status-icon"><Cpu size={20}/></div><div className="status-copy"><strong>推理服务</strong><span>{ready ? 'CPU 服务已就绪' : healthError ? '无法连接推理服务' : health ? '模型尚未就绪' : '正在检查服务状态'}</span></div><Badge variant={ready ? 'secondary' : 'outline'} className={ready ? 'ready-badge' : ''}>{ready ? '已就绪' : healthChecking && !health ? '检查中' : '不可用'}</Badge></div>
            <div className="service-detail"><span>MERT-v1-95M</span><span>CPU · 无校准</span></div>
            {health && <div className="queue-info">运行中 {health.queue.active} · 排队 {health.queue.queued} / {health.limits.max_queue_jobs}</div>}
            {(!ready || healthError) && <Alert className="service-alert"><Info/><AlertTitle>{healthError ? '健康检查失败' : health && !health.model.assets_available ? '缺少本地模型资产' : '暂时无法上传'}</AlertTitle><AlertDescription>{healthError || health?.model.reason || '正在获取后端健康状态，上传将在服务就绪后开放。'}{health && !health.model.assets_available && <p>请在后端准备真实模型资产。此页面不会生成随机预测或示例分数。</p>}</AlertDescription></Alert>}
            <Button variant="ghost" className="refresh-button" onClick={analysis.refreshHealth} disabled={healthChecking}><RefreshCw size={14}/> {healthChecking ? '正在检查' : '重新检查服务'}</Button>
          </CardContent></Card>
          <Card className="panel upload-panel"><CardHeader><div className="section-number">01 / 输入</div><CardTitle>选择一段音乐</CardTitle><CardDescription>保留原始听感，将格式与时长检查交给后端。</CardDescription></CardHeader><CardContent>
            <div className={`upload-area ${busy ? 'is-busy' : ''}`} onDragOver={event => event.preventDefault()} onDrop={event => { event.preventDefault(); select(event.dataTransfer.files[0]) }}>
              <div className="upload-symbol"><UploadCloud size={27}/></div><h3>{file ? '音乐已选择' : '把音乐拖到这里'}</h3><p>或使用下方文件选择器</p>
              <Label htmlFor="music-file" className="sr-only">选择音乐文件</Label><Input id="music-file" type="file" accept=".wav,.mp3,.flac,.ogg" disabled={busy} onChange={event => select(event.target.files?.[0])} className="file-input" aria-describedby="upload-limits"/>
              <span id="upload-limits" className="upload-limits">WAV / MP3 / FLAC / OGG<br/>M4A 请先转换为上述格式<br/>最大 {(maxBytes / 1024 / 1024).toFixed(0)} MB · {minDuration}–{maxDuration} 秒</span>
            </div>
            {file && <div className="selected-file"><FileAudio size={19}/><div><strong>{file.name}</strong><span>{(file.size / 1024 / 1024).toFixed(2)} MB · 本地预览</span></div>{!busy && <Button variant="ghost" onClick={() => { analysis.clearResult(); player.reset(); setFile(null); setLocalError(null); const input = document.getElementById('music-file') as HTMLInputElement | null; if (input) input.value = '' }}>移除</Button>}</div>}
            {audioUrl && <audio ref={player.audioRef} onTimeUpdate={player.onTimeUpdate} onSeeked={player.onTimeUpdate} key={audioUrl} src={audioUrl} controls preload="metadata" className="audio-preview" aria-label="所选音乐的本地预览"/>}
            {(localError || problem) && <p role="alert" className="file-error">{localError || problem}</p>}
            <Button size="lg" className="analyze-button" disabled={!ready || !file || !!problem || busy} onClick={() => { if (file) { player.reset(); void analysis.upload(file) } }}>{busy ? <LoaderCircle className="spinner"/> : <AudioLines/>}{uploading ? '正在上传音乐' : busy ? '正在分析，请稍候' : '开始情绪分析'}{!busy && <ArrowUpRight/>}</Button>
            <p className="privacy-note"><ShieldCheck size={14}/> 上传的声音由后端临时处理后删除，仅用于当前分析。请确认你有权使用该音频。</p>
          </CardContent></Card>
          {(job || error) && <Card className="panel task-panel"><CardContent><div className="task-heading"><strong>{uploading ? '上传音乐' : job ? stages[job.stage] : '任务提示'}</strong>{job?.status === 'completed' && <CheckCircle2 size={18} className="success-icon"/>}</div>{job && <>{job.status !== 'failed' && <Progress value={Math.max(0, Math.min(1, job.progress)) * 100} aria-label="后端任务进度"/>}<p className="task-caption">{job.status === 'failed' ? '任务已失败并停止查询，不会继续等待或生成结果。请检查错误后重新分析。' : job.status === 'completed' ? '当前音频的整体与可用窗口结果已返回。' : 'CPU 推理可能需要数分钟；每 2 秒查询状态，最多 20 分钟。'}</p></>}{error && <Alert variant="destructive" role="alert"><Info/><AlertTitle>需要关注</AlertTitle><AlertDescription>{error}</AlertDescription></Alert>}{paused && <Button variant="outline" onClick={analysis.resume} className="resume-button"><RefreshCw size={14}/> 恢复状态查询</Button>}</CardContent></Card>}
        </section>
        <section aria-label="情绪分析结果"><Card className="panel result-panel"><CardHeader><div className="result-heading"><div><div className="section-number">02 / 整体观察</div><CardTitle>音乐的情绪坐标</CardTitle></div><Badge variant="outline">整体静态预测</Badge></div><CardDescription>横轴是愉悦度，纵轴是唤醒度；两轴参考范围均为 [−1, 1]。</CardDescription></CardHeader><CardContent>
          <EmotionPlane result={result}/>
          <div className="metric-grid"><div className="metric"><span>愉悦度 <small>Valence</small></span><strong title={result ? `模型原始值：${result.valence}` : undefined}>{result ? formatScore(result.valence) : '—'}</strong><p>消极方向 ← 0 → 积极方向</p></div><div className="metric"><span>唤醒度 <small>Arousal</small></span><strong title={result ? `模型原始值：${result.arousal}` : undefined}>{result ? formatScore(result.arousal) : '—'}</strong><p>平静方向 ← 0 → 激动方向</p></div></div>
          {result?.out_of_range && <Alert className="range-alert"><Info/><AlertTitle>原始输出超出参考范围</AlertTitle><AlertDescription>上方数值以四位小数显示；悬停或导出查看原始值。仅整体二维图上的坐标使用 display 值裁剪到 [−1, 1]，没有改变原始预测。原始值不是概率。</AlertDescription></Alert>}
          {result && <div className="result-metadata"><span>音频时长 <b>{result.duration_seconds.toFixed(2)} s</b></span><span>处理耗时 <b>{result.processing_seconds.toFixed(2)} s</b></span><span>特征时间箱 <b>{result.feature_bins}</b></span><span>设备 <b>{result.device.toUpperCase()}</b></span><span>回归头种子 <b>{result.head_seed}</b></span><span>校准 <b>无</b></span><span className="revision">模型版本 <b>{result.model_revision}</b></span></div>}
          <Separator/><div className="interpretation"><Info size={17}/><p><strong>如何理解这些数值？</strong>积极 / 消极、平静 / 激动仅描述数值方向，并非可靠的情绪分类。输出未经校准，不代表概率、准确率或个人感受；此演示不是医疗工具，也不提供实时情绪轨迹。</p></div>
        </CardContent></Card></section>
      </div>
      <TimelinePanel result={result} currentTime={player.currentTime} selectedIndex={player.selectedIndex} onSelect={player.selectWindow}/>
      <footer className="page-footer"><span><FlaskConical size={14}/> 为研究与方法演示而设计</span><span>真实后端结果 · 无模拟分数 · 无外部音频服务</span></footer>
    </main>
  </div>
}
