import './App.css'
import { useEffect } from 'react'
import { BrowserRouter, Route, Routes, useNavigate } from 'react-router-dom'

import { GatewayStatus } from './components/layout/GatewayStatus'
import { RunWizard } from './components/runs/RunWizard'
import {
  completePairing,
  listRuns,
  pauseRun,
  resumeRun,
  startPairing,
  startRun,
  stopRun,
} from './lib/apiClient'
import { RunWorkspace } from './components/runs/RunWorkspace'
import { useRunsStore } from './stores/runs'
import { useSessionStore } from './stores/session'
import { useWSStore } from './stores/ws'

function RunsPage() {
  const runs = useRunsStore((state) => state.runs)
  const loading = useRunsStore((state) => state.loading)
  const selectedRunId = useRunsStore((state) => state.selectedRunId)
  const selectRun = useRunsStore((state) => state.selectRun)
  const timelineByRun = useRunsStore((state) => state.timelineByRun)
  const applyEvent = useRunsStore((state) => state.applyEvent)
  const token = useSessionStore((state) => state.token)
  const setRuns = useRunsStore((state) => state.setRuns)
  const errors = useWSStore((state) => state.errors)
  const clearErrors = useWSStore((state) => state.clearErrors)

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

  const timelineEvents = selectedRunId ? timelineByRun[selectedRunId] ?? [] : []

  return (
    <section className="runs-screen">
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
        onPauseRun={onPauseRun}
        onResumeRun={onResumeRun}
        onStopRun={onStopRun}
        onSelectRun={selectRun}
        onStartRun={onStartRun}
      />
      <RunWizard onStart={onStartRun} />
    </section>
  )
}

function SettingsPage() {
  return (
    <section>
      <h2>Settings</h2>
      <p>Dashboard preferences and policy controls.</p>
    </section>
  )
}

function Shell() {
  const navigate = useNavigate()
  const token = useSessionStore((state) => state.token)
  const setToken = useSessionStore((state) => state.setToken)
  const activeSummary = useRunsStore((state) => state.activeSummary)
  const setRuns = useRunsStore((state) => state.setRuns)
  const applyEvent = useRunsStore((state) => state.applyEvent)
  const setLoading = useRunsStore((state) => state.setLoading)
  const gatewayStatus = useWSStore((state) => state.status)
  const connect = useWSStore((state) => state.connect)
  const disconnect = useWSStore((state) => state.disconnect)

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
        if (active) {
          setRuns(runs.runs)
          connect(sessionToken, applyEvent)
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
  }, [applyEvent, connect, disconnect, setLoading, setRuns, setToken, token])

  return (
    <div className="app-shell">
      <GatewayStatus status={gatewayStatus} />
      <div className="body">
        <nav className="nav">
          <button type="button" onClick={() => navigate('/')}>
            Runs
          </button>
          <button type="button" onClick={() => navigate('/settings')}>
            Settings
          </button>
        </nav>
        <main className="content">
          <Routes>
            <Route path="/" element={<RunsPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Routes>
        </main>
      </div>
      <footer className="status-bar">{activeSummary}</footer>
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
