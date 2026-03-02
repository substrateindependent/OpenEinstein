import './App.css'
import { useEffect } from 'react'
import { BrowserRouter, Route, Routes, useNavigate } from 'react-router-dom'

import { completePairing, listRuns, startPairing, startRun } from './lib/apiClient'
import { useRunsStore } from './stores/runs'
import { useSessionStore } from './stores/session'
import { useWSStore } from './stores/ws'

function RunsPage() {
  const runs = useRunsStore((state) => state.runs)
  const loading = useRunsStore((state) => state.loading)
  const token = useSessionStore((state) => state.token)
  const setRuns = useRunsStore((state) => state.setRuns)

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
  }

  return (
    <section>
      <h2>Runs</h2>
      <p>Live campaign runs streamed from the gateway.</p>
      <button type="button" onClick={() => void onStartRun()} disabled={!token}>
        Start Run
      </button>
      {loading && <p>Loading runs...</p>}
      <ul>
        {runs.map((run) => (
          <li key={run.run_id}>
            {run.run_id} - {run.status}
          </li>
        ))}
      </ul>
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
      <header className="top-bar">
        <h1>OpenEinstein Control UI</h1>
        <p>Gateway: {gatewayStatus}</p>
      </header>
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
