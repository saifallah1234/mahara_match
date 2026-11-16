import assert from 'node:assert/strict'
import test from 'node:test'
import { formatCountdown, interviewDisplayState, openCapture, recordingAllowed, recordingMimeType, reviewMimeType } from '../src/lib/mockInterviewMachine.ts'
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

test('capture falls back to the microphone alone when the camera is missing or refused', async () => {
  const track = (kind) => ({ kind })
  const stream = (...kinds) => ({ getVideoTracks: () => kinds.filter((kind) => kind === 'video').map(track) })
  const asked = []
  const camera = await openCapture(async (constraints) => { asked.push(constraints); return stream('audio', 'video') })
  assert.equal(camera.audioOnly, false)
  assert.ok(asked[0].audio && asked[0].video)
  const refused = await openCapture(async (constraints) => { if (constraints.video) throw new DOMException('denied', 'NotAllowedError'); return stream('audio') })
  assert.equal(refused.audioOnly, true)
  await assert.rejects(openCapture(async () => { throw new DOMException('denied', 'NotAllowedError') }), /microphone est nécessaire/)
  assert.equal(reviewMimeType((mime) => mime === 'video/webm'), 'video/webm')
  assert.equal(reviewMimeType(() => false), null)
  assert.equal(formatCountdown(180), '3:00')
  assert.equal(formatCountdown(65), '1:05')
  assert.equal(formatCountdown(0), '0:00')
})
