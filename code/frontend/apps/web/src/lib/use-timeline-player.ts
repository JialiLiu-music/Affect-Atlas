import { useRef, useState } from 'react'
import type { TimelinePoint } from './api'

export function useTimelinePlayer() {
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const [currentTime, setCurrentTime] = useState(0)
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null)
  const selectWindow = (point: TimelinePoint) => {
    setSelectedIndex(point.index)
    if (audioRef.current) audioRef.current.currentTime = point.start_seconds
    setCurrentTime(point.start_seconds)
  }
  const reset = () => {
    audioRef.current?.pause()
    if (audioRef.current) audioRef.current.currentTime = 0
    setCurrentTime(0)
    setSelectedIndex(null)
  }
  return { audioRef, currentTime, selectedIndex, selectWindow, reset, onTimeUpdate: () => setCurrentTime(audioRef.current?.currentTime ?? 0) }
}
