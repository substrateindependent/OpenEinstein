import { create } from 'zustand'

import type { WSEvent } from '../types/ws'

type GatewayStatus = 'connected' | 'reconnecting' | 'disconnected'
type ErrorClassification = 'transient' | 'blocking' | 'fatal'

type ClassifiedError = {
  classification: ErrorClassification
  message: string
  ts: string
}

type WSStore = {
  status: GatewayStatus
  errors: ClassifiedError[]
  connect: (token: string, onEvent: (event: WSEvent) => void) => void
  disconnect: () => void
  clearErrors: () => void
  send: (message: Record<string, unknown>) => void
}

let activeSocket: WebSocket | null = null
let heartbeatInterval: ReturnType<typeof setInterval> | null = null
let reconnectTimer: ReturnType<typeof setTimeout> | null = null
let activeToken: string | null = null
let activeOnEvent: ((event: WSEvent) => void) | null = null
let heartbeatMisses = 0
let reconnectAttempts = 0
let manualDisconnect = false

function clearTimers() {
  if (heartbeatInterval) {
    clearInterval(heartbeatInterval)
    heartbeatInterval = null
  }
  if (reconnectTimer) {
    clearTimeout(reconnectTimer)
    reconnectTimer = null
  }
}

export const useWSStore = create<WSStore>((set, get) => {
  function scheduleReconnect() {
    if (manualDisconnect || !activeToken || !activeOnEvent) {
      return
    }
    const delayMs = Math.min(30_000, 1_000 * 2 ** reconnectAttempts)
    reconnectAttempts += 1
    set({ status: 'reconnecting' })
    reconnectTimer = setTimeout(() => {
      connectInternal(activeToken as string, activeOnEvent as (event: WSEvent) => void)
    }, delayMs)
  }

  function connectInternal(token: string, onEvent: (event: WSEvent) => void) {
    if (typeof WebSocket === 'undefined') {
      set({ status: 'disconnected' })
      return
    }

    if (activeSocket) {
      activeSocket.close()
      activeSocket = null
    }

    activeToken = token
    activeOnEvent = onEvent
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/ws/control?token=${encodeURIComponent(token)}`
    const socket = new WebSocket(wsUrl)
    activeSocket = socket
    set({ status: 'reconnecting' })

    socket.onopen = () => {
      reconnectAttempts = 0
      heartbeatMisses = 0
      set({ status: 'connected' })
      socket.send(JSON.stringify({ type: 'connect', payload: { token } }))
    }

    socket.onmessage = (event) => {
      heartbeatMisses = 0
      try {
        const payload = JSON.parse(event.data) as WSEvent
        if (payload.type === 'error') {
          const classification = String(payload.payload.classification ?? 'blocking') as ErrorClassification
          const message = String(payload.payload.message ?? 'Gateway reported an error.')
          const ts = String(payload.payload.ts ?? new Date().toISOString())
          set((state) => ({
            errors: [...state.errors, { classification, message, ts }],
          }))
        }
        onEvent(payload)
      } catch {
        // Ignore malformed messages from external clients.
      }
    }

    socket.onclose = () => {
      if (activeSocket === socket) {
        activeSocket = null
      }
      set({ status: 'disconnected' })
      scheduleReconnect()
    }

    if (!heartbeatInterval) {
      heartbeatInterval = setInterval(() => {
        if (!activeSocket) {
          return
        }
        heartbeatMisses += 1
        if (heartbeatMisses >= 9) {
          set({ status: 'reconnecting' })
          activeSocket.close()
        }
      }, 5_000)
    }
  }

  return {
    status: 'disconnected',
    errors: [],
    connect: (token, onEvent) => {
      manualDisconnect = false
      clearTimers()
      connectInternal(token, onEvent)
    },
    disconnect: () => {
      manualDisconnect = true
      clearTimers()
      activeSocket?.close()
      activeSocket = null
      activeToken = null
      activeOnEvent = null
      set({ status: 'disconnected' })
    },
    clearErrors: () => {
      if (get().errors.length > 0) {
        set({ errors: [] })
      }
    },
    send: (message) => {
      if (!activeSocket || activeSocket.readyState !== WebSocket.OPEN) {
        return
      }
      activeSocket.send(JSON.stringify(message))
    },
  }
})
