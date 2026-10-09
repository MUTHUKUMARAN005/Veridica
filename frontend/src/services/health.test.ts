import { afterEach, test } from 'node:test'
import assert from 'node:assert/strict'
import { getHealth } from './health.ts'

const originalFetch = globalThis.fetch
afterEach(() => { globalThis.fetch = originalFetch })

for (const status of [200, 503]) {
  test(`health client reports actual dependency state for HTTP ${status}`, async () => {
    const services = { postgres: status === 200 ? 'connected' : 'unavailable', redis: 'connected' }
    globalThis.fetch = async () => new Response(JSON.stringify({ services }), { status })
    assert.deepEqual(await getHealth(new AbortController().signal), { api: 'connected', ...services })
  })
}

for (const kind of ['failure', 'malformed', 'proxy-error']) {
  test(`health client does not invent dependency state: ${kind}`, async () => {
    globalThis.fetch = async () => {
      if (kind === 'failure') throw new Error('offline')
      return new Response('{}', { status: kind === 'proxy-error' ? 502 : 200 })
    }
    assert.deepEqual(await getHealth(new AbortController().signal), {
      api: 'unavailable', postgres: 'unknown', redis: 'unknown',
    })
  })
}