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

describe('App tools and settings wiring', () => {
  beforeEach(() => {
    vi.stubGlobal('WebSocket', MockWebSocket as unknown as typeof WebSocket)

    const responses: Record<string, unknown> = {
      'POST /api/v1/pair/start': { code: '123456' },
      'POST /api/v1/pair/complete': { token: 'token-1' },
      'GET /api/v1/runs': { runs: [{ run_id: 'run-1', status: 'running', started_at: '2026-03-01T00:00:00Z' }] },
      'GET /api/v1/approvals': { approvals: [] },
      'GET /api/v1/tools': {
        tools: [
          { id: 'sympy', status: 'available', latency_ms: 12 },
          { id: 'scanner', status: 'degraded', latency_ms: 140 },
        ],
      },
      'POST /api/v1/tools/sympy/test': { id: 'sympy', status: 'ok' },
      'GET /api/v1/config': {
        session_timeout_minutes: 480,
        notifications_enabled: true,
        allow_insecure_remote: false,
      },
      'POST /api/v1/config/validate': { valid: true, errors: [] },
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

  it('loads tools route and executes test-connection + settings validation', async () => {
    const user = userEvent.setup()
    render(<App />)
    await waitFor(() => expect(screen.getByText(/Run Detail/i)).toBeInTheDocument())

    await user.click(screen.getByRole('button', { name: /Tools/i }))
    expect(await screen.findByRole('heading', { name: /Tools/i })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /Test sympy/i }))
    expect(await screen.findByText(/sympy: ok/i)).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /Settings/i }))
    expect(await screen.findByRole('heading', { name: /Settings/i })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /Save settings/i }))
    expect(await screen.findByText(/Settings validated successfully/i)).toBeInTheDocument()
  })
})
