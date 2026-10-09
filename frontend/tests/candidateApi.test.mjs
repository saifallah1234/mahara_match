import assert from 'node:assert/strict'
import test from 'node:test'
import { publishedOffers, uploadCV } from '../src/api/candidate.ts'

const originalFetch = globalThis.fetch
globalThis.document = { cookie: '' }
const json = (body, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })

test('server filters and pagination retain results from every page', async () => {
  const calls = []
  globalThis.fetch = async (url) => {
    calls.push(url)
    return json(calls.length === 1 ? { results: [{ id: '1' }], next: 'page 2' } : { results: [{ id: '2' }], next: null })
  }
  try {
    assert.deepEqual((await publishedOffers('backend', 'Tunis')).map((offer) => offer.id), ['1', '2'])
    assert.match(calls[0], /status=PUBLISHED&search=backend&governorate=Tunis&page=1&page_size=100/)
    assert.match(calls[1], /page=2&page_size=100/)
  } finally { globalThis.fetch = originalFetch }
})

test('CV creation failure retains uploaded document ID for retry', async () => {
  const calls = []
  globalThis.fetch = async (url, init) => {
    calls.push({ url, init })
    if (calls.length === 1) return json({ id: 'document-1' }, 201)
    if (calls.length === 2) return json({ error: { message: 'CV creation failed' } }, 400)
    return json({ id: 'cv-1', document: 'document-1' }, 201)
  }
  const file = new File(['%PDF-1.7'], 'cv.pdf', { type: 'application/pdf' })
  try {
    let retained
    await assert.rejects(uploadCV(file, 'Mon CV'), (error) => { retained = error.documentId; return retained === 'document-1' })
    assert.equal(calls[0].init.body.get('type'), 'CV')
    assert.equal(calls[0].init.body.get('file').name, 'cv.pdf')
    assert.equal(calls[0].init.headers.has('Content-Type'), false)
    const retried = await uploadCV(file, 'Mon CV', retained)
    assert.equal(retried.cv.id, 'cv-1')
    assert.equal(calls.length, 3)
  } finally { globalThis.fetch = originalFetch }
})
