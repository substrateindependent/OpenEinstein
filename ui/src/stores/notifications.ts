import { useStore } from 'zustand'
import { createStore } from 'zustand/vanilla'

import type { WSEvent } from '../types/ws'

export type NotificationLevel = 'info' | 'warning' | 'error'

export type NotificationItem = {
  id: string
  level: NotificationLevel
  message: string
  ts: string
  read: boolean
}

type NotificationsStoreState = {
  items: NotificationItem[]
  unreadCount: number
  applyEvent: (event: WSEvent) => void
  markAllRead: () => void
}

function nowIso(): string {
  return new Date().toISOString()
}

function nextNotification(
  event: WSEvent,
  index: number,
): NotificationItem | null {
  if (event.type === 'approval_required') {
    return {
      id: `approval-${index}-${nowIso()}`,
      level: 'warning',
      message: `Approval required: ${String(event.payload.what ?? event.payload.action ?? 'action')}`,
      ts: nowIso(),
      read: false,
    }
  }
  if (event.type === 'cost_update') {
    const budgetPercent = Number(event.payload.budget_percent ?? 0)
    if (budgetPercent >= 80) {
      return {
        id: `cost-${index}-${nowIso()}`,
        level: 'warning',
        message: `Run is above 80% of budget (${budgetPercent.toFixed(0)}%).`,
        ts: nowIso(),
        read: false,
      }
    }
  }
  if (event.type === 'error') {
    return {
      id: `error-${index}-${nowIso()}`,
      level: 'error',
      message: String(event.payload.message ?? 'Gateway reported an error.'),
      ts: nowIso(),
      read: false,
    }
  }
  return null
}

export function createNotificationsStore() {
  return createStore<NotificationsStoreState>((set) => ({
    items: [],
    unreadCount: 0,
    applyEvent: (event) =>
      set((state) => {
        const candidate = nextNotification(event, state.items.length)
        if (!candidate) {
          return state
        }
        const items = [...state.items, candidate]
        return {
          items,
          unreadCount: items.filter((item) => !item.read).length,
        }
      }),
    markAllRead: () =>
      set((state) => {
        const items = state.items.map((item) => ({ ...item, read: true }))
        return {
          items,
          unreadCount: 0,
        }
      }),
  }))
}

const notificationsStore = createNotificationsStore()

export function useNotificationsStore<T>(selector: (state: NotificationsStoreState) => T): T {
  return useStore(notificationsStore, selector)
}
