import type { RunSummary } from '../../types/api'
import type { TimelineEvent } from '../../stores/runs'

type RunWorkspaceProps = {
  runs: RunSummary[]
  loading: boolean
  selectedRunId: string | null
  timelineEvents: TimelineEvent[]
  onPauseRun: (runId: string) => Promise<void>
  onResumeRun: (runId: string) => Promise<void>
  onStopRun: (runId: string) => Promise<void>
  onSelectRun: (runId: string) => void
  onStartRun: () => Promise<void>
}

export function RunWorkspace({
  runs,
  loading,
  selectedRunId,
  timelineEvents,
  onPauseRun,
  onResumeRun,
  onStopRun,
  onSelectRun,
  onStartRun,
}: RunWorkspaceProps) {
  return (
    <section className="run-workspace">
      <div className="run-toolbar">
        <h2>Run Detail</h2>
        <div className="toolbar-actions">
          <button type="button" onClick={() => void onStartRun()}>
            Start Run
          </button>
          <button
            type="button"
            onClick={() => selectedRunId && void onPauseRun(selectedRunId)}
            disabled={!selectedRunId}
          >
            Pause
          </button>
          <button
            type="button"
            onClick={() => selectedRunId && void onResumeRun(selectedRunId)}
            disabled={!selectedRunId}
          >
            Resume
          </button>
          <button
            type="button"
            onClick={() => selectedRunId && void onStopRun(selectedRunId)}
            disabled={!selectedRunId}
          >
            Stop
          </button>
        </div>
      </div>

      <div className="run-panels">
        <aside className="run-panel progress-panel">
          <h3>Progress Tracker</h3>
          {loading && <p>Loading runs...</p>}
          {!loading && runs.length === 0 && <p>No runs found.</p>}
          <ul>
            {runs.map((run) => (
              <li key={run.run_id}>
                <button type="button" onClick={() => onSelectRun(run.run_id)}>
                  {run.run_id} ({run.status})
                </button>
              </li>
            ))}
          </ul>
          <p>Selected run: {selectedRunId ?? 'none'}</p>
        </aside>

        <div className="run-panel timeline-panel">
          <h3>Timeline</h3>
          <ul>
            {timelineEvents.map((event, index) => (
              <li key={`${event.ts}-${index}`}>
                <details open>
                  <summary>{event.summary}</summary>
                  <pre>{JSON.stringify(event.payload, null, 2)}</pre>
                </details>
              </li>
            ))}
          </ul>
          {timelineEvents.length === 0 && <p>No timeline events yet.</p>}
        </div>

        <aside className="run-panel sidebar-panel">
          <h3>Artifacts</h3>
          <p>Artifact previews will appear here.</p>
          <h3>Cost</h3>
          <p>Cost breakdown panel is loading.</p>
        </aside>
      </div>
    </section>
  )
}
