import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import App from './App'

class MockWebSocket {
  static latest: MockWebSocket | null = null
  static OPEN = 1
  static CLOSED = 3

  url: string
  onopen: (() => void) | null = null
  onmessage: ((event: MessageEvent<string>) => void) | null = null
  onclose: (() => void) | null = null
  readyState = MockWebSocket.OPEN
  sent: string[] = []

  constructor(url: string) {
    this.url = url
    MockWebSocket.latest = this
  }

  send(payload: string) {
    this.sent.push(payload)
  }

  close() {
    this.readyState = MockWebSocket.CLOSED
    this.onclose?.()
  }
}

describe('App compare wiring', () => {
  beforeEach(() => {
    vi.stubGlobal('WebSocket', MockWebSocket as unknown as typeof WebSocket)
    const responses: Record<string, unknown> = {
      'POST /api/v1/pair/start': { code: '123456' },
      'POST /api/v1/pair/complete': { token: 'token-1' },
      'GET /api/v1/runs': {
        runs: [
          { run_id: 'run-1', status: 'running', started_at: '2026-03-01T00:00:00Z' },
          { run_id: 'run-2', status: 'failed', started_at: '2026-03-01T00:01:00Z' },
        ],
      },
      'GET /api/v1/approvals': { approvals: [] },
      'GET /api/v1/runs/compare?run_ids=run-1%2Crun-2': {
        runs: [
          { run_id: 'run-1', status: 'running', estimated_cost_usd: 2.2, confidence: 0.72, tags: ['baseline'] },
          { run_id: 'run-2', status: 'failed', estimated_cost_usd: 3.1, confidence: 0.3, tags: ['failed'] },
        ],
      },
      'POST /api/v1/runs/run-1/tags': { run_id: 'run-1', tags: ['candidate'] },
    }

    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const method = (init?.method ?? 'GET').toUpperCase()
        const requestUrl = String(input)
        const key = `${method} ${requestUrl}`
        const payload = responses[key]
        if (!payload) {
          return new Response(JSON.stringify({}), { status: 404 })
        }
        return new Response(JSON.stringify(payload), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        })
      }),
    )
  })

  it('loads compare route, runs compare request, and saves tags', async () => {
    const user = userEvent.setup()
    render(<App />)
    await waitFor(() => expect(screen.getByText(/Run Detail/i)).toBeInTheDocument())

    await user.click(screen.getByRole('button', { name: /Compare/i }))
    expect(await screen.findByRole('heading', { name: /Run Comparison/i })).toBeInTheDocument()

    await user.click(screen.getByRole('checkbox', { name: /run-1/i }))
    await user.click(screen.getByRole('checkbox', { name: /run-2/i }))
    await user.click(screen.getByRole('button', { name: /Compare selected runs/i }))
    expect(await screen.findByText(/Confidence: 0.30/i)).toBeInTheDocument()

    await user.clear(screen.getByLabelText(/Tag run-1/i))
    await user.type(screen.getByLabelText(/Tag run-1/i), 'candidate')
    await user.click(screen.getByRole('button', { name: /Save tag run-1/i }))

    const fetchMock = globalThis.fetch as unknown as ReturnType<typeof vi.fn>
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/runs/run-1/tags',
      expect.objectContaining({ method: 'POST' }),
    )
  })
})
