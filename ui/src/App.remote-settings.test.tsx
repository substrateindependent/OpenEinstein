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

describe('App remote + webhook settings wiring', () => {
  beforeEach(() => {
    vi.stubGlobal('WebSocket', MockWebSocket as unknown as typeof WebSocket)

    const responses: Record<string, unknown> = {
      'POST /api/v1/pair/start': { code: '123456' },
      'POST /api/v1/pair/complete': { token: 'token-1' },
      'GET /api/v1/runs': { runs: [] },
      'GET /api/v1/approvals': { approvals: [] },
      'GET /api/v1/config': {
        session_timeout_minutes: 480,
        notifications_enabled: true,
        allow_insecure_remote: false,
      },
      'POST /api/v1/config/validate': { valid: true, errors: [] },
      'POST /api/v1/system/remote/check': {
        allowed: false,
        message: 'Remote access requires HTTPS or tunnel.',
      },
      'POST /api/v1/system/webhook/test': {
        ok: true,
        message: 'Webhook dispatched.',
      },
      'POST /api/v1/system/email/test': {
        ok: true,
        message: 'Email dispatched.',
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

  it('checks remote safety and tests webhook/email channels from settings', async () => {
    const user = userEvent.setup()
    render(<App />)
    await waitFor(() => expect(screen.getByText(/Run Detail/i)).toBeInTheDocument())

    await user.click(screen.getByRole('button', { name: /Settings/i }))
    expect(await screen.findByRole('heading', { name: /Settings/i })).toBeInTheDocument()

    await user.type(screen.getByLabelText(/Remote origin/i), 'http://10.0.0.5:8420')
    await user.click(screen.getByRole('button', { name: /Check remote safety/i }))
    expect(await screen.findByText(/requires HTTPS or tunnel/i)).toBeInTheDocument()

    await user.type(screen.getByLabelText(/Webhook URL/i), 'https://hooks.example.com/oe')
    await user.click(screen.getByRole('button', { name: /Test webhook/i }))
    expect(await screen.findByText(/Webhook dispatched/i)).toBeInTheDocument()

    await user.type(screen.getByLabelText(/Email target/i), 'team@example.com')
    await user.click(screen.getByRole('button', { name: /Test email/i }))
    expect(await screen.findByText(/Email dispatched/i)).toBeInTheDocument()
  })
})
