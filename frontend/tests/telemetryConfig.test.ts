import assert from 'node:assert/strict'
import test from 'node:test'
import {
  BrowserTelemetryConfig,
  type BrowserTelemetrySettings
} from '../src/telemetryConfig.ts'

test('browser telemetry stays disabled when collector settings are absent', () => {
  const settings: BrowserTelemetrySettings = {
    collectorUrl: undefined,
    publicApiKey: undefined
  }

  assert.equal(BrowserTelemetryConfig.isConfigured(settings), false)
})

test('browser telemetry requires both public collector settings', () => {
  const settings: BrowserTelemetrySettings = {
    collectorUrl: 'https://collector.example.com/collect',
    publicApiKey: undefined
  }

  assert.throws(
    () => BrowserTelemetryConfig.isConfigured(settings),
    /VITE_FARO_URL and VITE_FARO_API_KEY/
  )
})

test('API trace propagation matches only the configured API origin', () => {
  const apiOriginPattern: RegExp = BrowserTelemetryConfig.getApiOriginPattern(
    'https://api.example.com/v1',
    'https://frontend.example.com'
  )

  assert.equal(
    apiOriginPattern.test('https://api.example.com/v1/parks'),
    true
  )
  assert.equal(
    apiOriginPattern.test('https://api.example.com.evil.test/parks'),
    false
  )
})
