import { act, render, screen, waitFor } from '@testing-library/react'
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

describe('App cost and notifications wiring', () => {
  beforeEach(() => {
    vi.stubGlobal('WebSocket', MockWebSocket as unknown as typeof WebSocket)
    const responses: Record<string, unknown> = {
      'POST /api/v1/pair/start': { code: '123456' },
      'POST /api/v1/pair/complete': { token: 'token-1' },
      'GET /api/v1/runs': { runs: [{ run_id: 'run-1', status: 'running', started_at: '2026-03-01T00:00:00Z' }] },
      'GET /api/v1/approvals': { approvals: [] },
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

  it('fans out cost_update to top bar, run panel, status bar, and notification drawer', async () => {
    const user = userEvent.setup()
    render(<App />)

    await waitFor(() => expect(screen.getByText(/Run Detail/i)).toBeInTheDocument())
    const socket = MockWebSocket.latest
    act(() => {
      socket?.onopen?.()
      socket?.onmessage?.(
        new MessageEvent('message', {
          data: JSON.stringify({
            type: 'cost_update',
            payload: {
              run_id: 'run-1',
              estimated_cost_usd: 12.5,
              token_count: 20000,
              budget_percent: 82,
            },
          }),
        }),
      )
    })

    expect(await screen.findByText(/Cost today: \$12.50/i)).toBeInTheDocument()
    expect(screen.getByText(/Current run: \$12.50/i)).toBeInTheDocument()
    expect(screen.getByText(/Cost: \$12.50/i)).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /Notifications \(1\)/i }))
    expect(screen.getByText(/80% of budget/i)).toBeInTheDocument()
  })
})
