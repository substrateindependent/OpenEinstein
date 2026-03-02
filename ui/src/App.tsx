import './App.css'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { BrowserRouter, Route, Routes, useNavigate } from 'react-router-dom'

import { ApprovalsCenter } from './components/approvals/ApprovalsCenter'
import { ArtifactsBrowser } from './components/artifacts/ArtifactsBrowser'
import { CommandPalette } from './components/commands/CommandPalette'
import { ComparePanel } from './components/compare/ComparePanel'
import { GatewayStatus } from './components/layout/GatewayStatus'
import { ApprovalBanner } from './components/runs/ApprovalBanner'
import { RunWizard } from './components/runs/RunWizard'
import { SettingsPanel } from './components/settings/SettingsPanel'
import { ToolsPanel } from './components/tools/ToolsPanel'
import {
  bulkDecideApprovals,
  compareRuns,
  decideApproval,
  exportRun,
  forkRun,
  listApprovals,
  listTools,
  listRunArtifacts,
  loadDashboardConfig,
  completePairing,
  listRuns,
  pauseRun,
  previewArtifact,
  resumeRun,
  startPairing,
  startRun,
  stopRun,
  testToolConnection,
  updateRunTags,
  validateDashboardConfig,
} from './lib/apiClient'
import { RunWorkspace } from './components/runs/RunWorkspace'
import type { ApprovalDecision } from './stores/approvals'
import { useApprovalsStore } from './stores/approvals'
import { useCostStore } from './stores/cost'
import { useNotificationsStore } from './stores/notifications'
import { useRunsStore } from './stores/runs'
import { useSessionStore } from './stores/session'
import { useWSStore } from './stores/ws'
import type { WSEvent } from './types/ws'

function RunsPage() {
  const runs = useRunsStore((state) => state.runs)
  const loading = useRunsStore((state) => state.loading)
  const selectedRunId = useRunsStore((state) => state.selectedRunId)
  const selectRun = useRunsStore((state) => state.selectRun)
  const timelineByRun = useRunsStore((state) => state.timelineByRun)
  const applyEvent = useRunsStore((state) => state.applyEvent)
  const token = useSessionStore((state) => state.token)
  const setRuns = useRunsStore((state) => state.setRuns)
  const pendingApprovals = useApprovalsStore((state) => state.pendingSorted)
  const applyApprovalEvent = useApprovalsStore((state) => state.applyEvent)
  const runCosts = useCostStore((state) => state.runCosts)
  const errors = useWSStore((state) => state.errors)
  const clearErrors = useWSStore((state) => state.clearErrors)
  const wsSend = useWSStore((state) => state.send)
  const [selectedEventIndex, setSelectedEventIndex] = useState<number | null>(null)
  const [verbosity, setVerbosity] = useState<'minimal' | 'normal' | 'verbose' | 'debug'>('normal')

  async function onStartRun() {
    if (!token) {
      return
    }
    const started = await startRun(token, 'campaigns/sample.yaml')
    setRuns([
      ...runs,
      {
        run_id: started.run_id,
        status: started.status,
        started_at: new Date().toISOString(),
      },
    ])
    applyEvent({
      type: 'run_event',
      payload: {
        run_id: started.run_id,
        summary: `Run started from ${'campaigns/sample.yaml'}`,
      },
    })
  }

  async function onPauseRun(runId: string) {
    if (!token) {
      return
    }
    const paused = await pauseRun(token, runId)
    applyEvent({ type: 'run_state', payload: { run_id: runId, status: paused.status } })
  }

  async function onResumeRun(runId: string) {
    if (!token) {
      return
    }
    const resumed = await resumeRun(token, runId)
    applyEvent({ type: 'run_state', payload: { run_id: runId, status: resumed.status } })
  }

  async function onStopRun(runId: string) {
    if (!token) {
      return
    }
    const stopped = await stopRun(token, runId)
    applyEvent({ type: 'run_state', payload: { run_id: runId, status: stopped.status } })
  }

  async function onForkFromEvent(eventIndex: number) {
    if (!token || !selectedRunId) {
      return
    }
    const forked = await forkRun(token, selectedRunId, eventIndex)
    setRuns([
      ...runs,
      {
        run_id: forked.run_id,
        status: forked.status,
        started_at: new Date().toISOString(),
      },
    ])
    applyEvent({ type: 'run_state', payload: { run_id: forked.run_id, status: forked.status } })
    selectRun(forked.run_id)
  }

  function onSetVerbosity(level: 'minimal' | 'normal' | 'verbose' | 'debug') {
    setVerbosity(level)
    wsSend({ type: 'set_verbosity', payload: { level } })
  }

  async function onDecideApproval(approvalId: string, decision: ApprovalDecision) {
    if (!token) {
      return
    }
    const pending = pendingApprovals.find((item) => item.approval_id === approvalId)
    if (!pending) {
      return
    }
    await decideApproval(token, approvalId, pending.action, decision)
    applyApprovalEvent({
      type: 'approval_resolved',
      payload: { approval_id: approvalId, decision },
    })
  }

  const timelineEvents = selectedRunId ? timelineByRun[selectedRunId] ?? [] : []
  useEffect(() => {
    if (timelineEvents.length === 0) {
      setSelectedEventIndex(null)
      return
    }
    setSelectedEventIndex((current) => {
      if (current === null || current >= timelineEvents.length) {
        return 0
      }
      return current
    })
  }, [timelineEvents])
  const inlineApprovals = selectedRunId
    ? pendingApprovals.filter((item) => item.run_id === selectedRunId)
    : pendingApprovals
  const selectedEvent = selectedEventIndex !== null ? timelineEvents[selectedEventIndex] ?? null : null
  const currentRunCostUsd = selectedRunId ? runCosts[selectedRunId]?.estimated_cost_usd ?? 0 : 0

  return (
    <section className="runs-screen">
      <ApprovalBanner pending={inlineApprovals} onDecide={onDecideApproval} />
      {errors.length > 0 && (
        <div className="error-stack" role="status" aria-label="Gateway errors">
          <div className="error-stack-header">
            <h2>Errors</h2>
            <button type="button" onClick={() => clearErrors()}>
              Clear
            </button>
          </div>
          <ul>
            {errors.map((error, index) => (
              <li key={`${error.ts}-${index}`} className={`error-card error-${error.classification}`}>
                <strong>{error.classification.toUpperCase()}</strong> {error.message}
              </li>
            ))}
          </ul>
        </div>
      )}
      <RunWorkspace
        runs={runs}
        loading={loading}
        selectedRunId={selectedRunId}
        timelineEvents={timelineEvents}
        selectedEventIndex={selectedEventIndex}
        selectedEvent={selectedEvent}
        verbosity={verbosity}
        onPauseRun={onPauseRun}
        onResumeRun={onResumeRun}
        onStopRun={onStopRun}
        onSelectRun={selectRun}
        onStartRun={onStartRun}
        onSetVerbosity={onSetVerbosity}
        onForkFromEvent={onForkFromEvent}
        onSelectEvent={setSelectedEventIndex}
        currentRunCostUsd={currentRunCostUsd}
      />
      <RunWizard onStart={onStartRun} />
    </section>
  )
}

function ApprovalsPage() {
  const token = useSessionStore((state) => state.token)
  const approvals = useApprovalsStore((state) => state.pendingSorted)
  const applyApprovalEvent = useApprovalsStore((state) => state.applyEvent)

  async function onDecide(approvalId: string, decision: ApprovalDecision) {
    if (!token) {
      return
    }
    const pending = approvals.find((item) => item.approval_id === approvalId)
    if (!pending) {
      return
    }
    await decideApproval(token, approvalId, pending.action, decision)
    applyApprovalEvent({
      type: 'approval_resolved',
      payload: { approval_id: approvalId, decision },
    })
  }

  async function onApproveLowRisk() {
    if (!token) {
      return
    }
    const lowRisk = approvals.filter((item) => item.risk === 'low')
    if (lowRisk.length === 0) {
      return
    }
    await bulkDecideApprovals(
      token,
      lowRisk.map((item) => ({ action: item.action, decision: 'approve' })),
    )
    for (const item of lowRisk) {
      applyApprovalEvent({
        type: 'approval_resolved',
        payload: { approval_id: item.approval_id, decision: 'approve' },
      })
    }
  }

  return (
    <ApprovalsCenter approvals={approvals} onDecide={onDecide} onApproveLowRisk={onApproveLowRisk} />
  )
}

function SettingsPage() {
  const token = useSessionStore((state) => state.token)
  const [settings, setSettings] = useState({
    session_timeout_minutes: 480,
    notifications_enabled: true,
    allow_insecure_remote: false,
  })

  useEffect(() => {
    if (!token) {
      return
    }
    let active = true
    void loadDashboardConfig(token).then((config) => {
      if (active) {
        setSettings(config)
      }
    })
    return () => {
      active = false
    }
  }, [token])

  async function onSave(nextSettings: {
    session_timeout_minutes: number
    notifications_enabled: boolean
    allow_insecure_remote: boolean
  }) {
    if (!token) {
      return { valid: false, errors: ['Missing session token'] }
    }
    return validateDashboardConfig(token, nextSettings)
  }

  return (
    <SettingsPanel
      key={`${settings.session_timeout_minutes}-${settings.notifications_enabled}-${settings.allow_insecure_remote}`}
      initialSettings={settings}
      onSave={onSave}
    />
  )
}

function ArtifactsPage() {
  const token = useSessionStore((state) => state.token)
  const selectedRunId = useRunsStore((state) => state.selectedRunId)
  const [artifacts, setArtifacts] = useState<Array<{ run_id: string; name: string; path: string; attached_at: string }>>(
    [],
  )
  const [selectedArtifactPath, setSelectedArtifactPath] = useState<string | null>(null)
  const [previewText, setPreviewText] = useState('')
  const [downloadUrl, setDownloadUrl] = useState<string | undefined>(undefined)

  useEffect(() => {
    if (!token || !selectedRunId) {
      setArtifacts([])
      setSelectedArtifactPath(null)
      setPreviewText('')
      return
    }
    let active = true
    void listRunArtifacts(token, selectedRunId).then((result) => {
      if (!active) {
        return
      }
      setArtifacts(result.artifacts)
      setSelectedArtifactPath(result.artifacts[0]?.path ?? null)
    })
    return () => {
      active = false
    }
  }, [selectedRunId, token])

  async function onSelectArtifact(path: string) {
    if (!token) {
      return
    }
    setSelectedArtifactPath(path)
    const artifactId = path.split('/').pop() ?? path
    const preview = await previewArtifact(token, artifactId)
    setPreviewText(preview.preview)
  }

  async function onExportRun() {
    if (!token || !selectedRunId) {
      return
    }
    const exported = await exportRun(token, selectedRunId)
    setDownloadUrl(exported.download_url)
    const refreshed = await listRunArtifacts(token, selectedRunId)
    setArtifacts(refreshed.artifacts)
  }

  return (
    <ArtifactsBrowser
      runId={selectedRunId}
      artifacts={artifacts}
      selectedArtifactPath={selectedArtifactPath}
      previewText={previewText}
      downloadUrl={downloadUrl}
      onSelectArtifact={onSelectArtifact}
      onExportRun={onExportRun}
    />
  )
}

function ToolsPage() {
  const token = useSessionStore((state) => state.token)
  const [tools, setTools] = useState<Array<{ id: string; status: string; latency_ms?: number }>>([])
  const [testResults, setTestResults] = useState<Record<string, string>>({})

  useEffect(() => {
    if (!token) {
      return
    }
    let active = true
    void listTools(token).then((result) => {
      if (active) {
        setTools(result.tools)
      }
    })
    return () => {
      active = false
    }
  }, [token])

  async function onTestConnection(toolId: string) {
    if (!token) {
      return
    }
    const result = await testToolConnection(token, toolId)
    setTestResults((state) => ({ ...state, [toolId]: result.status }))
    setTools((state) =>
      state.map((tool) => (tool.id === toolId ? { ...tool, status: result.status } : tool)),
    )
  }

  return <ToolsPanel tools={tools} testResults={testResults} onTestConnection={onTestConnection} />
}

function ComparePage() {
  const token = useSessionStore((state) => state.token)
  const runs = useRunsStore((state) => state.runs)
  const [selectedRunIds, setSelectedRunIds] = useState<string[]>([])
  const [comparedRuns, setComparedRuns] = useState<
    Array<{
      run_id: string
      status: 'running' | 'stopped' | 'completed' | 'failed'
      estimated_cost_usd: number
      confidence: number
      tags: string[]
    }>
  >([])
  const [tagFilter, setTagFilter] = useState('')

  async function onCompare() {
    if (!token || selectedRunIds.length < 2) {
      return
    }
    const response = await compareRuns(token, selectedRunIds)
    setComparedRuns(response.runs)
  }

  async function onUpdateTag(runId: string, tag: string) {
    if (!token) {
      return
    }
    const updated = await updateRunTags(token, runId, tag)
    setComparedRuns((state) =>
      state.map((item) => (item.run_id === runId ? { ...item, tags: updated.tags } : item)),
    )
  }

  const filtered = comparedRuns.filter((run) =>
    tagFilter.trim().length === 0 ? true : run.tags.some((tag) => tag.includes(tagFilter.trim())),
  )

  return (
    <section className="compare-page">
      <h2>Run Comparison</h2>
      <p>Select 2 to 5 runs for comparison.</p>
      <div className="compare-controls">
        {runs.map((run) => (
          <label key={run.run_id}>
            <input
              type="checkbox"
              checked={selectedRunIds.includes(run.run_id)}
              onChange={(event) =>
                setSelectedRunIds((state) =>
                  event.target.checked
                    ? [...state, run.run_id].slice(0, 5)
                    : state.filter((item) => item !== run.run_id),
                )
              }
            />
            {run.run_id}
          </label>
        ))}
      </div>
      <button type="button" onClick={() => void onCompare()}>
        Compare selected runs
      </button>
      <label>
        Filter by tag
        <input
          aria-label="Filter by tag"
          value={tagFilter}
          onChange={(event) => setTagFilter(event.target.value)}
        />
      </label>
      <ComparePanel comparedRuns={filtered} onUpdateTag={onUpdateTag} />
    </section>
  )
}

function Shell() {
  const navigate = useNavigate()
  const [notificationsOpen, setNotificationsOpen] = useState(false)
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false)
  const token = useSessionStore((state) => state.token)
  const setToken = useSessionStore((state) => state.setToken)
  const activeSummary = useRunsStore((state) => state.activeSummary)
  const selectedRunId = useRunsStore((state) => state.selectedRunId)
  const runs = useRunsStore((state) => state.runs)
  const setRuns = useRunsStore((state) => state.setRuns)
  const applyEvent = useRunsStore((state) => state.applyEvent)
  const applyApprovalEvent = useApprovalsStore((state) => state.applyEvent)
  const setPendingApprovals = useApprovalsStore((state) => state.setPending)
  const applyCostEvent = useCostStore((state) => state.applyEvent)
  const runCosts = useCostStore((state) => state.runCosts)
  const todayCostUsd = useCostStore((state) => state.todayCostUsd)
  const applyNotificationEvent = useNotificationsStore((state) => state.applyEvent)
  const notificationItems = useNotificationsStore((state) => state.items)
  const unreadNotifications = useNotificationsStore((state) => state.unreadCount)
  const markAllNotificationsRead = useNotificationsStore((state) => state.markAllRead)
  const setLoading = useRunsStore((state) => state.setLoading)
  const gatewayStatus = useWSStore((state) => state.status)
  const connect = useWSStore((state) => state.connect)
  const disconnect = useWSStore((state) => state.disconnect)
  const handleEvent = useCallback(
    (event: WSEvent) => {
      applyEvent(event)
      applyApprovalEvent(event)
      applyCostEvent(event)
      applyNotificationEvent(event)
    },
    [applyApprovalEvent, applyCostEvent, applyEvent, applyNotificationEvent],
  )

  useEffect(() => {
    let active = true

    async function bootstrap() {
      setLoading(true)
      try {
        let sessionToken = token
        if (!sessionToken) {
          const started = await startPairing()
          const completed = await completePairing(started.code)
          sessionToken = completed.token
          if (active) {
            setToken(sessionToken)
          }
        }

        const runs = await listRuns(sessionToken)
        const approvals = await listApprovals(sessionToken)
        if (active) {
          setRuns(runs.runs)
          setPendingApprovals(approvals.approvals)
          connect(sessionToken, handleEvent)
        }
      } catch {
        if (active) {
          disconnect()
        }
      } finally {
        if (active) {
          setLoading(false)
        }
      }
    }

    void bootstrap()
    return () => {
      active = false
      disconnect()
    }
  }, [connect, disconnect, handleEvent, setLoading, setPendingApprovals, setRuns, setToken, token])

  const selectedRunCost = selectedRunId ? runCosts[selectedRunId]?.estimated_cost_usd ?? 0 : 0

  const commandPaletteCommands = useMemo(
    () => [
      {
        id: 'go-runs',
        label: 'Open Runs',
        run: () => navigate('/'),
      },
      {
        id: 'go-approvals',
        label: 'Open Approvals',
        run: () => navigate('/approvals'),
      },
      {
        id: 'go-artifacts',
        label: 'Open Artifacts',
        run: () => navigate('/artifacts'),
      },
      {
        id: 'go-compare',
        label: 'Open Compare',
        run: () => navigate('/compare'),
      },
      {
        id: 'go-tools',
        label: 'Open Tools',
        run: () => navigate('/tools'),
      },
      {
        id: 'go-settings',
        label: 'Open Settings',
        run: () => navigate('/settings'),
      },
      {
        id: 'start-sample-run',
        label: 'Start Sample Run',
        run: async () => {
          if (!token) {
            return
          }
          const started = await startRun(token, 'campaigns/sample.yaml')
          setRuns([
            ...runs,
            {
              run_id: started.run_id,
              status: started.status,
              started_at: new Date().toISOString(),
            },
          ])
          applyEvent({
            type: 'run_event',
            payload: {
              run_id: started.run_id,
              summary: `Run started from ${'campaigns/sample.yaml'}`,
            },
          })
          navigate('/')
        },
      },
    ],
    [applyEvent, navigate, runs, setRuns, token],
  )

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        setCommandPaletteOpen(true)
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => {
      window.removeEventListener('keydown', onKeyDown)
    }
  }, [])

  return (
    <div className="app-shell">
      <GatewayStatus
        status={gatewayStatus}
        costTodayUsd={todayCostUsd}
        unreadNotifications={unreadNotifications}
        onToggleNotifications={() => setNotificationsOpen((value) => !value)}
        onOpenCommandPalette={() => setCommandPaletteOpen(true)}
      />
      <CommandPalette
        open={commandPaletteOpen}
        commands={commandPaletteCommands}
        onClose={() => setCommandPaletteOpen(false)}
      />
      {notificationsOpen && (
        <section className="notification-drawer" aria-label="Notifications">
          <div className="notification-drawer-header">
            <h2>Notifications</h2>
            <button type="button" onClick={() => markAllNotificationsRead()}>
              Mark all read
            </button>
          </div>
          {notificationItems.length === 0 ? (
            <p>No notifications.</p>
          ) : (
            <ul>
              {notificationItems.map((item) => (
                <li key={item.id} className={`notification-${item.level}`}>
                  {item.message}
                </li>
              ))}
            </ul>
          )}
        </section>
      )}
      <div className="body">
        <nav className="nav">
          <button type="button" onClick={() => navigate('/')}>
            Runs
          </button>
          <button type="button" onClick={() => navigate('/approvals')}>
            Approvals
          </button>
          <button type="button" onClick={() => navigate('/artifacts')}>
            Artifacts
          </button>
          <button type="button" onClick={() => navigate('/compare')}>
            Compare
          </button>
          <button type="button" onClick={() => navigate('/tools')}>
            Tools
          </button>
          <button type="button" onClick={() => navigate('/settings')}>
            Settings
          </button>
        </nav>
        <main className="content">
          <Routes>
            <Route path="/" element={<RunsPage />} />
            <Route path="/approvals" element={<ApprovalsPage />} />
            <Route path="/artifacts" element={<ArtifactsPage />} />
            <Route path="/compare" element={<ComparePage />} />
            <Route path="/tools" element={<ToolsPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Routes>
        </main>
      </div>
      <footer className="status-bar">
        {activeSummary} | Cost: ${selectedRunCost.toFixed(2)}
      </footer>
    </div>
  )
}

function App() {
  return (
    <BrowserRouter>
      <Shell />
    </BrowserRouter>
  )
}

export default App
