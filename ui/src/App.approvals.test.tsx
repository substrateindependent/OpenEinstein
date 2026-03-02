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

describe('App approvals wiring', () => {
  beforeEach(() => {
    vi.stubGlobal('WebSocket', MockWebSocket as unknown as typeof WebSocket)
    const responses: Record<string, unknown> = {
      'POST /api/v1/pair/start': { code: '123456' },
      'POST /api/v1/pair/complete': { token: 'token-1' },
      'GET /api/v1/runs': { runs: [{ run_id: 'run-1', status: 'running', started_at: '2026-03-01T00:00:00Z' }] },
      'GET /api/v1/approvals': { approvals: [] },
      'POST /api/v1/approvals/a-high/decide': { approval_id: 'a-high', status: 'approved' },
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

  it('mounts approval banner from websocket events and posts decisions', async () => {
    const user = userEvent.setup()
    render(<App />)

    await waitFor(() => expect(screen.getByText(/Run Detail/i)).toBeInTheDocument())

    const socket = MockWebSocket.latest
    expect(socket).not.toBeNull()
    act(() => {
      socket?.onopen?.()
      socket?.onmessage?.(
        new MessageEvent('message', {
          data: JSON.stringify({
            type: 'approval_required',
            payload: {
              approval_id: 'a-high',
              run_id: 'run-1',
              risk: 'high',
              what: 'shell execution',
              why: 'run export',
              action: 'shell_exec',
            },
          }),
        }),
      )
    })

    expect(await screen.findByText(/Approval Required/i)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /approve a-high/i }))

    const fetchMock = globalThis.fetch as unknown as ReturnType<typeof vi.fn>
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/approvals/a-high/decide',
      expect.objectContaining({ method: 'POST' }),
    )
  })
})
