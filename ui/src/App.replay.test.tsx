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

describe('App replay and verbosity wiring', () => {
  beforeEach(() => {
    vi.stubGlobal('WebSocket', MockWebSocket as unknown as typeof WebSocket)
    const responses: Record<string, unknown> = {
      'POST /api/v1/pair/start': { code: '123456' },
      'POST /api/v1/pair/complete': { token: 'token-1' },
      'GET /api/v1/runs': {
        runs: [{ run_id: 'run-1', status: 'running', started_at: '2026-03-01T00:00:00Z' }],
      },
      'GET /api/v1/approvals': { approvals: [] },
      'POST /api/v1/runs/run-1/fork': { run_id: 'run-fork-1', status: 'running' },
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

  it('sets verbosity via websocket and forks from selected timeline event', async () => {
    const user = userEvent.setup()
    render(<App />)
    await waitFor(() => expect(screen.getByText(/Run Detail/i)).toBeInTheDocument())

    const socket = MockWebSocket.latest
    act(() => {
      socket?.onopen?.()
      socket?.onmessage?.(
        new MessageEvent('message', {
          data: JSON.stringify({
            type: 'run_event',
            payload: {
              run_id: 'run-1',
              summary: 'Event for replay',
              ts: '2026-03-01T00:05:00Z',
            },
          }),
        }),
      )
    })

    await user.selectOptions(screen.getByLabelText(/Verbosity/i), 'verbose')
    await user.click(screen.getByRole('button', { name: /Re-run from here/i }))

    expect(socket?.sent.some((payload) => payload.includes('"type":"set_verbosity"'))).toBe(true)
    const fetchMock = globalThis.fetch as unknown as ReturnType<typeof vi.fn>
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/runs/run-1/fork',
      expect.objectContaining({ method: 'POST' }),
    )
  })
})
