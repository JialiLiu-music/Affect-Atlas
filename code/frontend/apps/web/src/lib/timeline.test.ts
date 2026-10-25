import { afterEach, describe, expect, it, vi } from 'vitest'
import { downloadPrediction, formatDelta, formatScore, formatSeconds, nearestWindow, predictionJson, scoreDomain, timelineCsv } from './timeline'
import { predictionFixture, windowFixtures } from './timeline.fixtures'

afterEach(() => vi.restoreAllMocks())
describe('timeline pure utilities', () => {
  it('formats display only, preserving near-zero direction in raw data', () => {
    expect(formatScore(.123456789)).toBe('0.1235')
    expect(formatScore(-.00001234)).toBe('-0.0000')
    expect(formatSeconds(7.123)).toBe('7.12 s')
    expect(formatDelta(.5, .25)).toBe('+0.2500')
    expect(formatDelta(-.5, .25)).toBe('-0.7500')
    expect(windowFixtures[1].valence).toBe(-.00001234)
  })
  it('selects nearest containing centers with deterministic overlap ties', () => {
    expect(nearestWindow(windowFixtures, 0)?.index).toBe(0)
    expect(nearestWindow(windowFixtures, 7.5)?.index).toBe(0)
    expect(nearestWindow(windowFixtures, 9)?.index).toBe(1)
    expect(nearestWindow(windowFixtures, 17)?.index).toBe(2)
    expect(nearestWindow(windowFixtures, 20)?.index).toBe(2)
    expect(nearestWindow([], 0)).toBeNull()
  })
  it('expands both sides of the domain for raw unbounded scores', () => {
    expect(scoreDomain(windowFixtures)).toEqual([-1.4, 1.23456789])
    expect(scoreDomain([])).toEqual([-1, 1])
  })
  it('exports BOM CSV with raw numeric windows and no names or tokens', () => {
    expect(timelineCsv(windowFixtures)).toBe('\uFEFFstart,end,center,bins,valence,arousal\r\n0,10,5,7,1.23456789,-0.25\r\n5,15,10,8,-0.00001234,-1.4\r\n7,17,12,8,0.4,0.8\r\n')
    expect(timelineCsv([])).toBe('\uFEFFstart,end,center,bins,valence,arousal\r\n\r\n')
    expect(timelineCsv([{ ...windowFixtures[0], valence: NaN }])).not.toContain('NaN')
  })
  it('exports the entire prediction with disclaimer and full precision only', () => {
    expect(JSON.parse(predictionJson(predictionFixture))).toEqual(predictionFixture)
    expect(predictionJson(predictionFixture)).not.toContain('access_token')
  })
  it('uses fixed safe download filenames and revokes object URLs', () => {
    const create = vi.fn(() => 'blob:test-export')
    const revoke = vi.fn()
    vi.stubGlobal('URL', { createObjectURL: create, revokeObjectURL: revoke })
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function (this: HTMLAnchorElement) {
      expect(this.download).toBe('music-affect-prediction.json')
      expect(this.href).toBe('blob:test-export')
    })
    downloadPrediction(predictionFixture, 'json')
    expect(click).toHaveBeenCalledOnce()
    expect(create).toHaveBeenCalledOnce()
    expect(revoke).toHaveBeenCalledWith('blob:test-export')
    expect(document.querySelector('a')).toBeNull()
    vi.unstubAllGlobals()
  })
})
