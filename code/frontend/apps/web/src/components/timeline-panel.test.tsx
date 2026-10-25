import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { TimelinePanel } from './timeline-panel'
import { predictionFixture } from '@/lib/timeline.fixtures'
import { useTimelinePlayer } from '@/lib/use-timeline-player'
import type { Prediction } from '@/lib/api'

afterEach(() => { cleanup(); vi.restoreAllMocks() })
function Harness({ result = predictionFixture }: { result?: Prediction | null }) {
  const player = useTimelinePlayer()
  return <><audio ref={player.audioRef} onTimeUpdate={player.onTimeUpdate} onSeeked={player.onTimeUpdate} aria-label="test player"/><button onClick={player.reset}>Reset file</button><TimelinePanel result={result} currentTime={player.currentTime} selectedIndex={player.selectedIndex} onSelect={player.selectWindow}/></>
}
describe('window selection and local playback', () => {
  it('uses the requested neutral title while retaining the static-model explanation', () => {
    const result = { ...predictionFixture, timeline: { ...predictionFixture.timeline!, disclaimer: '探索性窗口评分：静态模型窗口输出，非逐秒动态识别。' } }
    const { container } = render(<Harness result={result}/>)
    expect(screen.getByText('滑动窗口评分')).toBeTruthy()
    expect(container.textContent).not.toContain('探索性')
    expect(screen.getByText('窗口评分：静态模型窗口输出，非逐秒动态识别。')).toBeTruthy()
  })
  it('selects a button window, seeks to start without calling play and displays raw details', () => {
    const play = vi.spyOn(HTMLMediaElement.prototype, 'play').mockResolvedValue()
    const { container } = render(<Harness/>)
    const buttons = screen.getAllByRole('button', { name: /窗口/ })
    fireEvent.click(buttons[1])
    expect(buttons[1].getAttribute('aria-pressed')).toBe('true')
    expect(container.querySelector('audio')?.currentTime).toBe(5)
    expect(play).not.toHaveBeenCalled()
    expect(screen.getByText('已选窗口 2')).toBeTruthy()
    expect(screen.getByTitle('模型原始值：-0.00001234')).toBeTruthy()
    expect(screen.getByText('相对整体 -0.1235')).toBeTruthy()
  })
  it('synchronizes playhead and overlap highlight while retaining pause position', () => {
    const { container } = render(<Harness/>)
    const audio = container.querySelector('audio')!
    const initialX = screen.getByTestId('playhead').getAttribute('x1')
    audio.currentTime = 11.9
    fireEvent.timeUpdate(audio)
    const movedX = screen.getByTestId('playhead').getAttribute('x1')
    expect(movedX).not.toBe(initialX)
    expect(screen.getAllByRole('button', { name: /窗口/ })[2].className).toContain('playing-window')
    fireEvent.pause(audio)
    expect(screen.getByTestId('playhead').getAttribute('x1')).toBe(movedX)
    expect(screen.getByText('播放位置 11.90 s')).toBeTruthy()
  })
  it('selects an actual SVG point and resets selection and playback for a cleared file', () => {
    const pause = vi.spyOn(HTMLMediaElement.prototype, 'pause').mockImplementation(() => {})
    const { container } = render(<Harness/>)
    fireEvent.click(container.querySelectorAll('.curve-point')[2])
    expect(container.querySelector('audio')?.currentTime).toBe(7)
    expect(screen.getByText('已选窗口 3')).toBeTruthy()
    fireEvent.click(screen.getByText('Reset file'))
    expect(pause).toHaveBeenCalledOnce()
    expect(container.querySelector('audio')?.currentTime).toBe(0)
    expect(screen.queryByText('已选窗口 3')).toBeNull()
    expect(screen.getAllByRole('button', { name: /窗口/ }).every(button => button.getAttribute('aria-pressed') === 'false')).toBe(true)
  })
  it('shows one raw point per score without interpolating a short clip', () => {
    const point = { ...predictionFixture.timeline!.points[0], start_seconds: 0, end_seconds: 3, center_seconds: 1.5 }
    const { container } = render(<Harness result={{ ...predictionFixture, duration_seconds: 3, timeline: { ...predictionFixture.timeline!, points: [point] } }}/>)
    expect(container.querySelector('polyline')).toBeNull()
    expect(container.querySelectorAll('.curve-point')).toHaveLength(2)
    expect(screen.getByText(/仅一个整段窗口/)).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: /窗口 1/ }))
    expect(screen.getByTitle('模型原始值：1.23456789')).toBeTruthy()
  })
  it('keeps legacy and empty tasks free of fabricated points and disables CSV', () => {
    const legacy = { ...predictionFixture }
    delete legacy.timeline
    const { container, rerender } = render(<Harness result={legacy}/>)
    expect(screen.getByText(/此旧任务只有整体结果/)).toBeTruthy()
    expect(container.querySelector('.timeline-chart')).toBeNull()
    expect(screen.getByRole('button', { name: '导出时间窗 CSV' }).hasAttribute('disabled')).toBe(true)
    expect(screen.getByRole('button', { name: '导出完整 JSON' }).hasAttribute('disabled')).toBe(false)
    rerender(<Harness result={null}/>)
    expect(screen.getByText(/当前没有曲线数据/)).toBeTruthy()
    expect(screen.queryByTestId('playhead')).toBeNull()
  })
})
