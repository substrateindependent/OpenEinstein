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

describe('natural language commands and responsive layout wiring', () => {
  beforeEach(() => {
    vi.stubGlobal('WebSocket', MockWebSocket as unknown as typeof WebSocket)
    Object.defineProperty(window, 'innerWidth', { value: 760, writable: true })
    window.dispatchEvent(new Event('resize'))

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
      'POST /api/v1/intent/command': {
        action: 'navigate',
        route: '/settings',
        message: 'Navigating to /settings',
        resolved_role: 'fast',
        resolved_model: { provider: 'local', model: 'intent-router' },
        toolbus_used: false,
      },
    }

    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const method = (init?.method ?? 'GET').toUpperCase()
        const requestUrl = String(input)
        const payload = responses[`${method} ${requestUrl}`]
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

  it('persists layout preferences and routes natural-language commands through backend intent API', async () => {
    const user = userEvent.setup()
    render(<App />)
    await waitFor(() => expect(screen.getByText(/Run Detail/i)).toBeInTheDocument())

    const nav = document.querySelector('.nav')
    expect(nav).not.toBeNull()
    expect(nav?.getAttribute('data-open')).toBe('false')

    await user.click(screen.getByRole('button', { name: /Toggle navigation/i }))
    expect(nav?.getAttribute('data-open')).toBe('true')

    await user.click(screen.getByRole('button', { name: /Layout/i }))
    expect(await screen.findByRole('heading', { name: /Layout Customization/i })).toBeInTheDocument()
    await user.click(screen.getByRole('radio', { name: /Focus timeline/i }))
    await user.click(screen.getByRole('checkbox', { name: /Compact navigation labels/i }))

    await user.click(screen.getByRole('button', { name: /Runs/i }))
    const runPanels = document.querySelector('.run-panels')
    expect(runPanels?.className).toContain('layout-focus_timeline')
    expect(localStorage.getItem('openeinstein-layout')).toContain('focus_timeline')

    await user.click(screen.getByRole('button', { name: /Command Palette/i }))
    await user.click(screen.getByLabelText(/Natural language mode/i))
    await user.type(screen.getByLabelText(/Natural language command/i), 'open settings')
    await user.click(screen.getByRole('button', { name: /Run NL command/i }))

    const fetchMock = globalThis.fetch as unknown as ReturnType<typeof vi.fn>
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/intent/command',
      expect.objectContaining({ method: 'POST' }),
    )
    expect(await screen.findByRole('heading', { name: /Settings/i })).toBeInTheDocument()
  })
})
