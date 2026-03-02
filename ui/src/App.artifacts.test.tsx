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

describe('App artifacts wiring', () => {
  beforeEach(() => {
    vi.stubGlobal('WebSocket', MockWebSocket as unknown as typeof WebSocket)

    const responses: Record<string, unknown> = {
      'POST /api/v1/pair/start': { code: '123456' },
      'POST /api/v1/pair/complete': { token: 'token-1' },
      'GET /api/v1/runs': { runs: [{ run_id: 'run-1', status: 'running', started_at: '2026-03-01T00:00:00Z' }] },
      'GET /api/v1/approvals': { approvals: [] },
      'GET /api/v1/runs/run-1/artifacts': {
        artifacts: [
          {
            run_id: 'run-1',
            name: 'Summary CSV',
            path: '.openeinstein/exports/summary.csv',
            attached_at: '2026-03-01T00:00:00Z',
          },
        ],
      },
      'GET /api/v1/artifacts/summary.csv/preview': {
        artifact_id: 'summary.csv',
        mode: 'text',
        preview: 'col_a,col_b',
      },
      'POST /api/v1/runs/run-1/export': {
        run_id: 'run-1',
        download_url: '/api/v1/artifacts/run-1-paper-pack.zip/download',
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

  it('mounts artifacts route, previews files, and triggers run export', async () => {
    const user = userEvent.setup()
    render(<App />)

    await waitFor(() => expect(screen.getByText(/Run Detail/i)).toBeInTheDocument())

    await user.click(screen.getByRole('button', { name: /Artifacts/i }))
    expect(await screen.findByRole('heading', { name: /Artifacts/i })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /Summary CSV/i }))
    expect(await screen.findByText(/col_a,col_b/i)).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /Export Paper Pack/i }))
    expect(await screen.findByRole('link', { name: /Download Paper Pack/i })).toHaveAttribute(
      'href',
      '/api/v1/artifacts/run-1-paper-pack.zip/download',
    )
  })
})
