import { create } from 'zustand'

import type { WSEvent } from '../types/ws'

type GatewayStatus = 'connected' | 'reconnecting' | 'disconnected'

type WSStore = {
  status: GatewayStatus
  connect: (token: string, onEvent: (event: WSEvent) => void) => void
  disconnect: () => void
}

let activeSocket: WebSocket | null = null

export const useWSStore = create<WSStore>((set) => ({
  status: 'disconnected',
  connect: (token, onEvent) => {
    if (typeof WebSocket === 'undefined') {
      set({ status: 'disconnected' })
      return
    }
    if (activeSocket) {
      activeSocket.close()
      activeSocket = null
    }
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/ws/control?token=${encodeURIComponent(token)}`
    const socket = new WebSocket(wsUrl)
    activeSocket = socket
    set({ status: 'reconnecting' })

    socket.onopen = () => {
      set({ status: 'connected' })
      socket.send(JSON.stringify({ type: 'connect', payload: { token } }))
    }
    socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data) as WSEvent
        onEvent(payload)
      } catch {
        // Ignore malformed messages from external clients.
      }
    }
    socket.onclose = () => {
      set({ status: 'disconnected' })
      if (activeSocket === socket) {
        activeSocket = null
      }
    }
  },
  disconnect: () => {
    activeSocket?.close()
    activeSocket = null
    set({ status: 'disconnected' })
  },
}))
