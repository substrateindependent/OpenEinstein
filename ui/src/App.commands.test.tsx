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

describe('App command palette wiring', () => {
  beforeEach(() => {
    vi.stubGlobal('WebSocket', MockWebSocket as unknown as typeof WebSocket)
    const responses: Record<string, unknown> = {
      'POST /api/v1/pair/start': { code: '123456' },
      'POST /api/v1/pair/complete': { token: 'token-1' },
      'GET /api/v1/runs': { runs: [] },
      'GET /api/v1/approvals': { approvals: [] },
      'POST /api/v1/runs': { run_id: 'run-created', status: 'running' },
      'GET /api/v1/config': {
        session_timeout_minutes: 480,
        notifications_enabled: true,
        allow_insecure_remote: false,
      },
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

  it('dispatches navigation and mutation commands', async () => {
    const user = userEvent.setup()
    render(<App />)
    await waitFor(() => expect(screen.getByText(/Run Detail/i)).toBeInTheDocument())

    await user.click(screen.getByRole('button', { name: /Command Palette/i }))
    await user.type(screen.getByLabelText(/Command search/i), 'settings')
    await user.click(screen.getByRole('button', { name: /Open Settings/i }))
    expect(await screen.findByRole('heading', { name: /Settings/i })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /Command Palette/i }))
    await user.clear(screen.getByLabelText(/Command search/i))
    await user.type(screen.getByLabelText(/Command search/i), 'start sample run')
    await user.click(screen.getByRole('button', { name: /Start Sample Run/i }))

    const fetchMock = globalThis.fetch as unknown as ReturnType<typeof vi.fn>
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/runs',
      expect.objectContaining({ method: 'POST' }),
    )
  })
})
