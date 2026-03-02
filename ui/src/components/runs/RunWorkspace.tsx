import type { RunSummary } from '../../types/api'
import type { TimelineEvent } from '../../stores/runs'
import { useLayoutStore } from '../../stores/layout'

type RunWorkspaceProps = {
  runs: RunSummary[]
  loading: boolean
  selectedRunId: string | null
  timelineEvents: TimelineEvent[]
  selectedEventIndex: number | null
  selectedEvent: TimelineEvent | null
  verbosity: 'minimal' | 'normal' | 'verbose' | 'debug'
  onPauseRun: (runId: string) => Promise<void>
  onResumeRun: (runId: string) => Promise<void>
  onStopRun: (runId: string) => Promise<void>
  onSelectRun: (runId: string) => void
  onStartRun: () => Promise<void>
  onSetVerbosity: (level: 'minimal' | 'normal' | 'verbose' | 'debug') => void
  onForkFromEvent: (eventIndex: number) => Promise<void>
  onSelectEvent: (eventIndex: number) => void
  currentRunCostUsd: number
}

export function RunWorkspace({
  runs,
  loading,
  selectedRunId,
  timelineEvents,
  selectedEventIndex,
  selectedEvent,
  verbosity,
  onPauseRun,
  onResumeRun,
  onStopRun,
  onSelectRun,
  onStartRun,
  onSetVerbosity,
  onForkFromEvent,
  onSelectEvent,
  currentRunCostUsd,
}: RunWorkspaceProps) {
  const panelLayout = useLayoutStore((state) => state.panelLayout)

  return (
    <section className="run-workspace">
      <div className="run-toolbar">
        <h2>Run Detail</h2>
        <div className="toolbar-actions">
          <label>
            Verbosity
            <select
              aria-label="Verbosity"
              value={verbosity}
              onChange={(event) =>
                onSetVerbosity(event.target.value as 'minimal' | 'normal' | 'verbose' | 'debug')
              }
            >
              <option value="minimal">minimal</option>
              <option value="normal">normal</option>
              <option value="verbose">verbose</option>
              <option value="debug">debug</option>
            </select>
          </label>
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

      <div className={`run-panels layout-${panelLayout}`}>
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
                <details open={selectedEventIndex === index}>
                  <summary>{event.summary}</summary>
                  <button type="button" onClick={() => onSelectEvent(index)}>
                    Inspect
                  </button>
                  <pre>{JSON.stringify(event.payload, null, 2)}</pre>
                </details>
              </li>
            ))}
          </ul>
          {timelineEvents.length === 0 && <p>No timeline events yet.</p>}
          {selectedEvent && (
            <div className="event-inspector">
              <h4>Event Inspector</h4>
              <pre>{JSON.stringify(selectedEvent.payload, null, 2)}</pre>
              <button
                type="button"
                onClick={() =>
                  selectedEventIndex !== null && void onForkFromEvent(selectedEventIndex)
                }
                disabled={selectedEventIndex === null}
              >
                Re-run from here
              </button>
            </div>
          )}
        </div>

        <aside className="run-panel sidebar-panel">
          <h3>Artifacts</h3>
          <p>Artifact previews will appear here.</p>
          <h3>Cost</h3>
          <p>Current run: ${currentRunCostUsd.toFixed(2)}</p>
        </aside>
      </div>
    </section>
  )
}
