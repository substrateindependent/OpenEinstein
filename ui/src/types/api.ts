export type RunStatus = 'running' | 'stopped' | 'completed' | 'failed'

export type RunSummary = {
  run_id: string
  status: RunStatus
  started_at: string
  updated_at?: string
}

export type RunsResponse = {
  runs: RunSummary[]
}

export type StartRunResponse = {
  run_id: string
  status: RunStatus
}
