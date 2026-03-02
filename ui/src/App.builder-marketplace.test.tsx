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

describe('builder and marketplace wiring', () => {
  beforeEach(() => {
    vi.stubGlobal('WebSocket', MockWebSocket as unknown as typeof WebSocket)
    const installedPacks: Array<{ id: string; path: string }> = [{ id: 'installed-pack', path: '/packs/installed-pack' }]

    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const method = (init?.method ?? 'GET').toUpperCase()
        const requestUrl = String(input)

        if (method === 'POST' && requestUrl === '/api/v1/pair/start') {
          return new Response(JSON.stringify({ code: '123456' }), { status: 200 })
        }
        if (method === 'POST' && requestUrl === '/api/v1/pair/complete') {
          return new Response(JSON.stringify({ token: 'token-1' }), { status: 200 })
        }
        if (method === 'GET' && requestUrl === '/api/v1/runs') {
          return new Response(JSON.stringify({ runs: [] }), { status: 200 })
        }
        if (method === 'GET' && requestUrl === '/api/v1/approvals') {
          return new Response(JSON.stringify({ approvals: [] }), { status: 200 })
        }
        if (method === 'GET' && requestUrl === '/api/v1/config') {
          return new Response(
            JSON.stringify({
              session_timeout_minutes: 480,
              notifications_enabled: true,
              allow_insecure_remote: false,
            }),
            { status: 200 },
          )
        }
        if (method === 'GET' && requestUrl === '/api/v1/packs') {
          return new Response(JSON.stringify({ packs: installedPacks }), { status: 200 })
        }
        if (method === 'GET' && requestUrl === '/api/v1/packs/marketplace') {
          return new Response(
            JSON.stringify({
              packs: [
                {
                  id: 'market-pack',
                  name: 'Market Pack',
                  description: 'Market test pack',
                  trust_tier: 'curated',
                  installed: installedPacks.some((pack) => pack.id === 'market-pack'),
                },
              ],
            }),
            { status: 200 },
          )
        }
        if (method === 'POST' && requestUrl === '/api/v1/packs/install') {
          installedPacks.push({ id: 'market-pack', path: '/packs/market-pack' })
          return new Response(
            JSON.stringify({
              pack_id: 'market-pack',
              installed_path: '/packs/market-pack',
              scan_findings: [],
            }),
            { status: 200 },
          )
        }
        if (method === 'GET' && requestUrl === '/api/v1/packs/installed-pack/schema') {
          return new Response(
            JSON.stringify({
              pack_id: 'installed-pack',
              campaign_path: 'campaign-packs/installed-pack/campaign.yaml',
              title: 'Installed Pack',
              description: 'Installed pack schema',
              fields: [
                {
                  name: 'search_space.generator_skill',
                  label: 'Generator Skill',
                  type: 'string',
                  required: true,
                  default: 'installed-skill',
                },
              ],
            }),
            { status: 200 },
          )
        }
        if (method === 'GET' && requestUrl === '/api/v1/packs/market-pack/schema') {
          return new Response(
            JSON.stringify({
              pack_id: 'market-pack',
              campaign_path: 'campaign-packs/market-pack/campaign.yaml',
              title: 'Market Pack',
              description: 'Market pack schema',
              fields: [
                {
                  name: 'search_space.generator_skill',
                  label: 'Generator Skill',
                  type: 'string',
                  required: true,
                  default: 'market-skill',
                },
              ],
            }),
            { status: 200 },
          )
        }
        if (method === 'POST' && requestUrl === '/api/v1/runs') {
          return new Response(JSON.stringify({ run_id: 'run-builder', status: 'running' }), {
            status: 200,
          })
        }
        return new Response(JSON.stringify({}), { status: 404 })
      }),
    )
  })

  it('installs marketplace pack and starts a run from generated builder schema', async () => {
    const user = userEvent.setup()
    render(<App />)
    await waitFor(() => expect(screen.getByText(/Run Detail/i)).toBeInTheDocument())

    await user.click(screen.getByRole('button', { name: /Marketplace/i }))
    expect(await screen.findByRole('heading', { name: /Pack Marketplace/i })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /Install/i }))
    expect(await screen.findByText(/Installed market-pack with no scan findings/i)).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /Builder/i }))
    expect(await screen.findByRole('heading', { name: /Campaign Builder/i })).toBeInTheDocument()
    await waitFor(() => expect(screen.getByRole('option', { name: 'market-pack' })).toBeInTheDocument())
    await user.selectOptions(screen.getByLabelText(/Campaign pack/i), 'market-pack')
    await user.click(screen.getByRole('button', { name: /Start run from builder/i }))

    const fetchMock = globalThis.fetch as unknown as ReturnType<typeof vi.fn>
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/runs',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ campaign_path: 'campaign-packs/market-pack/campaign.yaml' }),
      }),
    )
    expect(await screen.findByRole('heading', { name: /Run Detail/i })).toBeInTheDocument()
  })
})
