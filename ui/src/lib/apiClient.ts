import type {
  ApprovalDecision,
  ApprovalsResponse,
  ArtifactPreviewResponse,
  ArtifactsResponse,
  ConfigValidationResponse,
  DashboardSettings,
  ExportRunResponse,
  ForkRunResponse,
  RunsResponse,
  StartRunResponse,
  ToolsResponse,
} from '../types/api'

async function parseJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`)
  }
  return (await response.json()) as T
}

export async function startPairing(baseUrl = ''): Promise<{ code: string }> {
  const response = await fetch(`${baseUrl}/api/v1/pair/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  })
  return parseJson<{ code: string }>(response)
}

export async function completePairing(
  code: string,
  baseUrl = '',
): Promise<{ token: string }> {
  const response = await fetch(`${baseUrl}/api/v1/pair/complete`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code }),
  })
  return parseJson<{ token: string }>(response)
}

export async function listRuns(token: string, baseUrl = ''): Promise<RunsResponse> {
  const response = await fetch(`${baseUrl}/api/v1/runs`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  return parseJson<RunsResponse>(response)
}

export async function startRun(
  token: string,
  campaignPath: string,
  baseUrl = '',
): Promise<StartRunResponse> {
  const response = await fetch(`${baseUrl}/api/v1/runs`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ campaign_path: campaignPath }),
  })
  return parseJson<StartRunResponse>(response)
}

export async function pauseRun(token: string, runId: string, baseUrl = ''): Promise<StartRunResponse> {
  const response = await fetch(`${baseUrl}/api/v1/runs/${runId}/pause`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
  })
  return parseJson<StartRunResponse>(response)
}

export async function resumeRun(
  token: string,
  runId: string,
  baseUrl = '',
): Promise<StartRunResponse> {
  const response = await fetch(`${baseUrl}/api/v1/runs/${runId}/resume`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
  })
  return parseJson<StartRunResponse>(response)
}

export async function stopRun(token: string, runId: string, baseUrl = ''): Promise<StartRunResponse> {
  const response = await fetch(`${baseUrl}/api/v1/runs/${runId}/stop`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
  })
  return parseJson<StartRunResponse>(response)
}

export async function listApprovals(token: string, baseUrl = ''): Promise<ApprovalsResponse> {
  const response = await fetch(`${baseUrl}/api/v1/approvals`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  return parseJson<ApprovalsResponse>(response)
}

export async function decideApproval(
  token: string,
  approvalId: string,
  action: string,
  decision: ApprovalDecision,
  baseUrl = '',
): Promise<{ approval_id: string; status: string }> {
  const response = await fetch(`${baseUrl}/api/v1/approvals/${approvalId}/decide`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      action,
      decision,
    }),
  })
  return parseJson<{ approval_id: string; status: string }>(response)
}

export async function bulkDecideApprovals(
  token: string,
  approvals: Array<{ action: string; decision: ApprovalDecision }>,
  baseUrl = '',
): Promise<{ processed: number }> {
  const response = await fetch(`${baseUrl}/api/v1/approvals/bulk`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ approvals }),
  })
  return parseJson<{ processed: number }>(response)
}

export async function listRunArtifacts(
  token: string,
  runId: string,
  baseUrl = '',
): Promise<ArtifactsResponse> {
  const response = await fetch(`${baseUrl}/api/v1/runs/${runId}/artifacts`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  return parseJson<ArtifactsResponse>(response)
}

export async function previewArtifact(
  token: string,
  artifactId: string,
  baseUrl = '',
): Promise<ArtifactPreviewResponse> {
  const response = await fetch(`${baseUrl}/api/v1/artifacts/${encodeURIComponent(artifactId)}/preview`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  return parseJson<ArtifactPreviewResponse>(response)
}

export async function exportRun(
  token: string,
  runId: string,
  baseUrl = '',
): Promise<ExportRunResponse> {
  const response = await fetch(`${baseUrl}/api/v1/runs/${runId}/export`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
  })
  return parseJson<ExportRunResponse>(response)
}

export async function forkRun(
  token: string,
  runId: string,
  eventIndex: number,
  baseUrl = '',
): Promise<ForkRunResponse> {
  const response = await fetch(`${baseUrl}/api/v1/runs/${runId}/fork`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ event_index: eventIndex }),
  })
  return parseJson<ForkRunResponse>(response)
}

export async function listTools(token: string, baseUrl = ''): Promise<ToolsResponse> {
  const response = await fetch(`${baseUrl}/api/v1/tools`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  return parseJson<ToolsResponse>(response)
}

export async function testToolConnection(
  token: string,
  toolId: string,
  baseUrl = '',
): Promise<{ id: string; status: string }> {
  const response = await fetch(`${baseUrl}/api/v1/tools/${encodeURIComponent(toolId)}/test`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
  })
  return parseJson<{ id: string; status: string }>(response)
}

export async function loadDashboardConfig(token: string, baseUrl = ''): Promise<DashboardSettings> {
  const response = await fetch(`${baseUrl}/api/v1/config`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  return parseJson<DashboardSettings>(response)
}

export async function validateDashboardConfig(
  token: string,
  config: DashboardSettings,
  baseUrl = '',
): Promise<ConfigValidationResponse> {
  const response = await fetch(`${baseUrl}/api/v1/config/validate`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      config: {
        model_routing: {},
        gateway: { controlUi: config },
      },
    }),
  })
  return parseJson<ConfigValidationResponse>(response)
}
