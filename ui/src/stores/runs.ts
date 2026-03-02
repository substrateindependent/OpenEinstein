import { createStore } from 'zustand/vanilla'
import { useStore } from 'zustand'

import type { RunStatus, RunSummary } from '../types/api'
import type { WSEvent } from '../types/ws'

type RunsStoreState = {
  runs: RunSummary[]
  activeSummary: string
  loading: boolean
  setRuns: (runs: RunSummary[]) => void
  setLoading: (value: boolean) => void
  applyEvent: (message: WSEvent) => void
}

function computeSummary(runs: RunSummary[]): string {
  const active = runs.find((run) => run.status === 'running')
  if (active) {
    return `Active run: ${active.run_id} (${active.status})`
  }
  if (runs.length > 0) {
    const latest = runs[runs.length - 1]
    return `Last run: ${latest.run_id} (${latest.status})`
  }
  return 'No active runs.'
}

export function createRunsStore() {
  return createStore<RunsStoreState>((set) => ({
    runs: [],
    activeSummary: 'No active runs.',
    loading: false,
    setRuns: (runs) => set(() => ({ runs, activeSummary: computeSummary(runs) })),
    setLoading: (value) => set(() => ({ loading: value })),
    applyEvent: (message) =>
      set((state) => {
        if (message.type !== 'run_state') {
          return state
        }
        const runId = String(message.payload.run_id ?? '')
        const status = String(message.payload.status ?? '') as RunStatus
        const hasRun = state.runs.some((run) => run.run_id === runId)
        const runs = hasRun
          ? state.runs.map((run) => (run.run_id === runId ? { ...run, status } : run))
          : [
              ...state.runs,
              { run_id: runId, status, started_at: new Date().toISOString() },
            ]
        return { runs, activeSummary: computeSummary(runs) }
      }),
  }))
}

const runsStore = createRunsStore()

export function useRunsStore<T>(selector: (state: RunsStoreState) => T): T {
  return useStore(runsStore, selector)
}
