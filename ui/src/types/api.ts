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

export type ApprovalRisk = 'low' | 'medium' | 'high'
export type ApprovalDecision = 'approve' | 'deny'

export type ApprovalRecord = {
  approval_id: string
  run_id: string
  risk: ApprovalRisk
  what: string
  why: string
  action: string
  requested_at: string
}

export type ApprovalsResponse = {
  approvals: ApprovalRecord[]
}

export type ArtifactRecord = {
  run_id: string
  name: string
  path: string
  attached_at: string
}

export type ArtifactsResponse = {
  artifacts: ArtifactRecord[]
}

export type ArtifactPreviewResponse = {
  artifact_id: string
  mode: 'text' | 'image' | 'pdf'
  preview: string
  download_url?: string
}

export type ExportRunResponse = {
  run_id: string
  download_url: string
}

export type ForkRunResponse = {
  run_id: string
  status: RunStatus
  parent_run_id?: string
}

export type ToolRecord = {
  id: string
  status: string
  latency_ms?: number
  error?: string
}

export type ToolsResponse = {
  tools: ToolRecord[]
}

export type DashboardSettings = {
  session_timeout_minutes: number
  notifications_enabled: boolean
  allow_insecure_remote: boolean
}

export type ConfigValidationResponse = {
  valid: boolean
  errors: string[]
}

export type ComparedRun = {
  run_id: string
  status: RunStatus
  estimated_cost_usd: number
  confidence: number
  tags: string[]
}

export type CompareRunsResponse = {
  runs: ComparedRun[]
}
