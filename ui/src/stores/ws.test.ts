import { beforeEach, describe, expect, it, vi } from 'vitest'

import { useWSStore } from './ws'

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

describe('ws store', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.stubGlobal('WebSocket', MockWebSocket as unknown as typeof WebSocket)
    vi.stubGlobal('window', {
      location: { protocol: 'http:', host: '127.0.0.1:8420' },
    })
    useWSStore.setState({ status: 'disconnected', errors: [] })
  })

  it('tracks connect state, heartbeat timeout, and classified errors', () => {
    useWSStore.getState().connect('token', () => undefined)
    const socket = MockWebSocket.latest
    expect(socket).not.toBeNull()

    socket?.onopen?.()
    expect(useWSStore.getState().status).toBe('connected')
    useWSStore.getState().send({ type: 'set_verbosity', payload: { level: 'debug' } })
    expect(socket?.sent.some((item) => item.includes('set_verbosity'))).toBe(true)

    socket?.onmessage?.(
      new MessageEvent('message', {
        data: JSON.stringify({
          type: 'error',
          payload: { classification: 'blocking', message: 'approval required' },
        }),
      }),
    )
    expect(useWSStore.getState().errors[0]?.classification).toBe('blocking')

    vi.advanceTimersByTime(46_000)
    expect(useWSStore.getState().status).toBe('reconnecting')
  })
})
