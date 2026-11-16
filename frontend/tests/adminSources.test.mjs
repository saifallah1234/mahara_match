// Placement: frontend/tests/adminSources.test.mjs
import assert from 'node:assert/strict'
import test from 'node:test'
import { canLaunch, sourcePayload } from '../src/lib/adminSources.ts'

test('a source form sends name, type and configuration, and a blank base URL as null', () => {
  assert.deepEqual(
    sourcePayload({ name: 'Tanitjobs', type: 'API', base_url: '', configuration: '{"query":"python"}' }),
    { ok: true, body: { name: 'Tanitjobs', type: 'API', base_url: null, configuration_json: { query: 'python' } } },
  )
})

test('a blank configuration is sent as an empty object, so an edit can clear it', () => {
  const result = sourcePayload({ name: 'Export CSV', type: 'CSV', base_url: 'https://example.tn/offres', configuration: '  ' })
  assert.deepEqual(result, { ok: true, body: { name: 'Export CSV', type: 'CSV', base_url: 'https://example.tn/offres', configuration_json: {} } })
})

test('a configuration that is not JSON stops the form before any request', () => {
  const result = sourcePayload({ name: 'Export CSV', type: 'CSV', base_url: '', configuration: '{oops' })
  assert.equal(result.ok, false)
  assert.match(result.error, /JSON/)
})

test('only an authorized web-scraping source offers the launch button', () => {
  assert.equal(canLaunch({ type: 'WEB_SCRAPING', is_authorized: true }), true)
  assert.equal(canLaunch({ type: 'WEB_SCRAPING', is_authorized: false }), false)
  assert.equal(canLaunch({ type: 'CSV', is_authorized: true }), false)
})
