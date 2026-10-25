import { Info } from 'lucide-react'
import { Alert, AlertDescription, AlertTitle } from '@workspace/ui/components/alert'
import { Badge } from '@workspace/ui/components/badge'
import { Button } from '@workspace/ui/components/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@workspace/ui/components/card'
import type { Prediction, TimelinePoint } from '@/lib/api'
import { downloadPrediction, formatDelta, formatScore, formatSeconds, nearestWindow, scoreDomain } from '@/lib/timeline'

interface Props {
  result: Prediction | null
  currentTime: number
  selectedIndex: number | null
  onSelect: (point: TimelinePoint) => void
}
export function TimelinePanel({ result, currentTime, selectedIndex, onSelect }: Props) {
  const points = result?.timeline?.points ?? []
  const selected = points.find(point => point.index === selectedIndex) ?? null
  const active = nearestWindow(points, currentTime)
  const [low, high] = scoreDomain(points)
  const duration = Math.max(1, result?.duration_seconds ?? 1, ...points.map(point => point.end_seconds))
  const x = (time: number) => 72 + time / duration * 876
  const y = (score: number) => 260 - (score - low) / (high - low) * 220
  const curves = [{ key: 'valence', label: '愉悦度 Valence', color: '#7053bd' }, { key: 'arousal', label: '唤醒度 Arousal', color: '#087f8c' }] as const
  return <section aria-label="窗口观察" className="timeline-section"><Card className="panel timeline-panel">
    <CardHeader><div className="result-heading"><div><div className="section-number">03 / 窗口观察</div><CardTitle>滑动窗口评分</CardTitle></div><Badge variant="outline">10 秒窗口 / 5 秒步长</Badge></div><CardDescription>复用一次完整音频的 MERT 特征，在时间窗内应用静态预测头。曲线仅连接窗口中心处的真实输出，连线不代表中间时刻的预测。</CardDescription></CardHeader>
    <CardContent>
      <Alert className="timeline-notice"><Info/><AlertTitle>窗口评分说明</AlertTitle><AlertDescription>这不是逐秒情绪轨迹或实时识别；未经平滑和校准，不应用论文中 13.5% 的校准效果。窗口可重叠，短于或等于 10 秒的音频只有一个整段窗口；长音频尾部追加末窗。{result?.timeline?.disclaimer && <p>{result.timeline.disclaimer.replace(/^探索性窗口评分：/, '窗口评分：')}</p>}</AlertDescription></Alert>
      {!points.length ? <div className="timeline-empty">{result ? result.timeline ? '后端未返回时间窗数据，无法绘制曲线；请检查后端后重新分析。' : '此旧任务只有整体结果。请重新分析以获取时间窗，不补造曲线。' : '完成真实分析后在此显示窗口评分；当前没有曲线数据。'}</div> : <>
        <div className="timeline-toolbar"><div className="curve-legend">{curves.map(curve => <span key={curve.key}><i style={{ background: curve.color }}/>{curve.label}</span>)}</div><span>播放位置 {formatSeconds(currentTime)}</span></div>
        {points.length === 1 && <p className="single-window-note">仅一个整段窗口：只有真实评分点，没有可观察的变化曲线，不插值连接。</p>}
        <div className="timeline-chart-scroll"><svg viewBox="0 0 1000 325" role="img" aria-label="窗口评分图：横轴秒，纵轴归一化评分。使用下方按钮可通过键盘选择窗口。" className="timeline-chart">
          {[0, 1, 2, 3, 4].map(tick => { const score = low + (high - low) * tick / 4; return <g key={tick}><line x1="72" x2="948" y1={y(score)} y2={y(score)} stroke="#e1e5ef"/><text x="60" y={y(score) + 4} textAnchor="end" className="tick">{score.toFixed(2)}</text><text x={x(duration * tick / 4)} y="284" textAnchor="middle" className="tick">{(duration * tick / 4).toFixed(1)}</text></g> })}
          {selected && <rect x={x(selected.start_seconds)} y="40" width={Math.max(1, x(selected.end_seconds) - x(selected.start_seconds))} height="220" fill="#7053bd" opacity=".07"/>}
          {curves.map(curve => <g key={curve.key}>
            {points.length > 1 && <polyline points={points.map(point => `${x(point.center_seconds)},${y(point[curve.key])}`).join(' ')} fill="none" stroke={curve.color} strokeWidth="2.5"/>}
            {points.map(point => <circle key={point.index} cx={x(point.center_seconds)} cy={y(point[curve.key])} r={point.index === selectedIndex ? 7 : 5} fill={curve.color} stroke="white" strokeWidth="2" onClick={() => onSelect(point)} className="curve-point"><title>窗口 {point.index + 1} · {formatSeconds(point.start_seconds)}–{formatSeconds(point.end_seconds)} · {curve.label} 原值 {point[curve.key]}</title></circle>)}
          </g>)}
          <line x1={x(Math.max(0, Math.min(duration, currentTime)))} x2={x(Math.max(0, Math.min(duration, currentTime)))} y1="32" y2="260" stroke="#48556d" strokeWidth="1.5" strokeDasharray="4 4" data-testid="playhead"/>
          <text x="510" y="315" textAnchor="middle" className="axis">音频时间（秒）</text><text x="18" y="150" textAnchor="middle" transform="rotate(-90 18 150)" className="axis">归一化评分（非概率）</text>
        </svg></div>
        <p className="window-help">点击图中评分点或下方片段按钮跳到窗口起点，不会自动播放。播放线与本地播放器同步，暂停时保留位置。深色边框表示已选窗口；“播放所在”按当前位置选择包含该时刻且中心最近的窗口，重叠处可能同时属于多个窗口。</p>
        <div className="window-list" aria-label="时间窗选择">{points.map(point => <Button key={point.index} variant="outline" aria-pressed={selectedIndex === point.index} onClick={() => onSelect(point)} className={`window-button ${active?.index === point.index ? 'playing-window' : ''}`}><span>窗口 {point.index + 1} · {formatSeconds(point.start_seconds)}–{formatSeconds(point.end_seconds)}</span><small>V {formatScore(point.valence)} · A {formatScore(point.arousal)}{active?.index === point.index ? ' · 播放所在' : ''}</small></Button>)}</div>
        {selected && result && <div className="window-detail" aria-live="polite"><strong>已选窗口 {selected.index + 1}</strong><p>起点 {formatSeconds(selected.start_seconds)} · 终点 {formatSeconds(selected.end_seconds)} · 中心 {formatSeconds(selected.center_seconds)} · 特征时间箱 {selected.feature_bins}</p><div className="metric-grid">{curves.map(curve => <div className="metric" key={curve.key}><span>{curve.label}</span><strong title={`模型原始值：${selected[curve.key]}`}>{formatScore(selected[curve.key])}</strong><p title={`原始差值：${selected[curve.key] - result[curve.key]}`}>相对整体 {formatDelta(selected[curve.key], result[curve.key])}</p></div>)}</div></div>}
        {(low < -1 || high > 1) && <p className="range-explanation">存在超出 [−1, 1] 的原始值，纵轴已自动扩展，曲线没有裁剪。</p>}
      </>}
      {result && <div className="export-actions"><Button variant="outline" onClick={() => downloadPrediction(result, 'json')}>导出完整 JSON</Button><Button variant="outline" disabled={!points.length} onClick={() => downloadPrediction(result, 'csv')}>导出时间窗 CSV</Button><span>四位小数仅用于阅读；悬停数值或导出查看原值。导出不含任务访问令牌。</span></div>}
    </CardContent>
  </Card></section>
}
