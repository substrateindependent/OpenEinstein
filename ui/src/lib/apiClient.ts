import type { RunsResponse, StartRunResponse } from '../types/api'

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
