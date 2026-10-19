import assert from 'node:assert/strict'
import test from 'node:test'
import { interviewDisplayState, recordingAllowed, recordingMimeType } from '../src/lib/mockInterviewMachine.ts'
import { answerInterview, createInterview } from '../src/api/mockInterviews.ts'

test('recording is allowed only while listening and server state restores the turn', () => {
  assert.equal(interviewDisplayState('IN_PROGRESS'), 'SPEAKING')
  assert.equal(interviewDisplayState('EVALUATING'), 'THINKING')
  for (const state of ['PREPARING', 'READY', 'INTRO', 'SPEAKING', 'UPLOADING', 'THINKING', 'FAILED', 'COMPLETED']) assert.equal(recordingAllowed(state), false)
  assert.equal(recordingAllowed('LISTENING'), true)
  assert.equal(recordingMimeType((mime) => mime === 'audio/webm'), 'audio/webm')
  assert.equal(recordingMimeType(() => false), null)
})

test('create and upload preserve idempotency key and expected version', async () => {
  const original = globalThis.fetch
  globalThis.document = { cookie: '' }
  const calls = []
  globalThis.fetch = async (url, init) => { calls.push({ url, init }); return new Response('{}', { headers: { 'Content-Type': 'application/json' } }) }
  try {
    await createInterview('offer', '', 'create-key')
    const session = { id: 'session', version: 7 }
    const answer = new Blob(['audio'], { type: 'audio/webm' })
    await answerInterview(session, 'turn', answer, 'answer-key')
    await answerInterview(session, 'turn', answer, 'answer-key')
    assert.equal(calls[0].init.headers.get('Idempotency-Key'), 'create-key')
    assert.equal(JSON.parse(calls[0].init.body).language, 'fr')
    assert.equal(calls[1].init.body.get('version'), '7')
    assert.equal(calls[1].init.headers.has('Content-Type'), false)
    assert.equal(calls[1].init.headers.get('Idempotency-Key'), calls[2].init.headers.get('Idempotency-Key'))
  } finally { globalThis.fetch = original }
})
