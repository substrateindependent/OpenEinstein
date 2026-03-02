import { useStore } from 'zustand'
import { createStore } from 'zustand/vanilla'

import type { RunStatus, RunSummary } from '../types/api'
import type { WSEvent } from '../types/ws'

export type TimelineEvent = {
  ts: string
  type: string
  summary: string
  payload: Record<string, unknown>
}

type RunsStoreState = {
  runs: RunSummary[]
  selectedRunId: string | null
  timelineByRun: Record<string, TimelineEvent[]>
  activeSummary: string
  loading: boolean
  setRuns: (runs: RunSummary[]) => void
  selectRun: (runId: string) => void
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
    selectedRunId: null,
    timelineByRun: {},
    activeSummary: 'No active runs.',
    loading: false,
    setRuns: (runs) =>
      set((state) => ({
        runs,
        selectedRunId: state.selectedRunId ?? runs[0]?.run_id ?? null,
        activeSummary: computeSummary(runs),
      })),
    selectRun: (runId) => set(() => ({ selectedRunId: runId })),
    setLoading: (value) => set(() => ({ loading: value })),
    applyEvent: (message) =>
      set((state) => {
        const runId = String(
          message.payload.run_id ?? state.selectedRunId ?? state.runs[0]?.run_id ?? '',
        )

        if (message.type === 'run_state') {
          const status = String(message.payload.status ?? '') as RunStatus
          const hasRun = state.runs.some((run) => run.run_id === runId)
          const runs = hasRun
            ? state.runs.map((run) => (run.run_id === runId ? { ...run, status } : run))
            : [
                ...state.runs,
                { run_id: runId, status, started_at: new Date().toISOString() },
              ]
          return {
            ...state,
            runs,
            selectedRunId: state.selectedRunId ?? runId,
            activeSummary: computeSummary(runs),
          }
        }

        if (!runId) {
          return state
        }
        const summary = String(message.payload.summary ?? message.type)
        const ts = String(message.payload.ts ?? new Date().toISOString())
        const event: TimelineEvent = { ts, type: message.type, summary, payload: message.payload }

        return {
          ...state,
          timelineByRun: {
            ...state.timelineByRun,
            [runId]: [...(state.timelineByRun[runId] ?? []), event],
          },
        }
      }),
  }))
}

const runsStore = createRunsStore()

export function useRunsStore<T>(selector: (state: RunsStoreState) => T): T {
  return useStore(runsStore, selector)
}
