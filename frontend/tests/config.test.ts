import assert from 'node:assert/strict'
import test from 'node:test'
import { Config } from '../src/config.ts'

test('frontend config provides local defaults when Vite settings are absent', () => {
  assert.equal(Config.API_BASE_URL, 'http://127.0.0.1:8000')
  assert.equal(Config.APP_NAME, 'chipark-frontend')
  assert.equal(Config.APP_VERSION, 'development')
  assert.deepEqual(Config.browserTelemetrySettings, {
    collectorUrl: undefined,
    publicApiKey: undefined
  })
})
