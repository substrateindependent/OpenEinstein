import { useStore } from 'zustand'
import { createStore } from 'zustand/vanilla'

import type { WSEvent } from '../types/ws'

export type RunCost = {
  run_id: string
  estimated_cost_usd: number
  token_count: number
  budget_percent: number
}

type CostStoreState = {
  runCosts: Record<string, RunCost>
  todayCostUsd: number
  setRunCost: (runId: string, cost: RunCost) => void
  applyEvent: (event: WSEvent) => void
}

function toNumber(value: unknown): number {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : 0
}

export function createCostStore() {
  return createStore<CostStoreState>((set) => ({
    runCosts: {},
    todayCostUsd: 0,
    setRunCost: (runId, cost) =>
      set((state) => {
        const runCosts = { ...state.runCosts, [runId]: cost }
        return {
          runCosts,
          todayCostUsd: Object.values(runCosts).reduce((sum, item) => sum + item.estimated_cost_usd, 0),
        }
      }),
    applyEvent: (event) =>
      set((state) => {
        if (event.type !== 'cost_update') {
          return state
        }
        const runId = String(event.payload.run_id ?? '')
        if (!runId) {
          return state
        }
        const runCosts = {
          ...state.runCosts,
          [runId]: {
            run_id: runId,
            estimated_cost_usd: toNumber(event.payload.estimated_cost_usd),
            token_count: toNumber(event.payload.token_count),
            budget_percent: toNumber(event.payload.budget_percent),
          },
        }
        return {
          runCosts,
          todayCostUsd: Object.values(runCosts).reduce((sum, item) => sum + item.estimated_cost_usd, 0),
        }
      }),
  }))
}

const costStore = createCostStore()

export function useCostStore<T>(selector: (state: CostStoreState) => T): T {
  return useStore(costStore, selector)
}
