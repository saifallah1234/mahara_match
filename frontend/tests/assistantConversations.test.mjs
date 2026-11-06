// Placement: frontend/tests/assistantConversations.test.mjs
import assert from 'node:assert/strict'
import test from 'node:test'
import { sortByActivity } from '../src/lib/assistantConversations.ts'

test('conversations list the most recent activity first, falling back to creation', () => {
  const conversations = [
    { id: 'old', title: '', last_message_at: '2026-10-01T09:00:00Z', created_at: '2026-10-01T08:00:00Z' },
    { id: 'empty', title: '', last_message_at: null, created_at: '2026-10-10T08:00:00Z' },
    { id: 'recent', title: '', last_message_at: '2026-10-20T07:00:00Z', created_at: '2026-10-05T08:00:00Z' },
  ]
  assert.deepEqual(sortByActivity(conversations).map((item) => item.id), ['recent', 'empty', 'old'])
  assert.deepEqual(conversations.map((item) => item.id), ['old', 'empty', 'recent'])
})
