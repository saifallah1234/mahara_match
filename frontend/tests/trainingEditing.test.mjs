import assert from 'node:assert/strict'
import test from 'node:test'
import { toDateTimeInput } from '../src/lib/format.ts'

test('an edited session shows the same wall-clock time the create form sent', () => {
  const input = '2026-11-03T09:05'
  const iso = new Date(input).toISOString()
  assert.equal(toDateTimeInput(iso), input)
})
