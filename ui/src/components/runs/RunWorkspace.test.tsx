import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'

import type { RunSummary } from '../../types/api'
import type { TimelineEvent } from '../../stores/runs'
import { RunWorkspace } from './RunWorkspace'

const runs: RunSummary[] = [
  {
    run_id: 'run-100',
    status: 'running',
    started_at: '2026-03-02T00:00:00Z',
  },
  {
    run_id: 'run-101',
    status: 'stopped',
    started_at: '2026-03-02T00:10:00Z',
  },
]

const timeline: TimelineEvent[] = [
  {
    ts: '2026-03-02T00:00:10Z',
    type: 'run_event',
    summary: 'Started literature phase',
    payload: { detail: 'phase=literature' },
  },
]

describe('RunWorkspace', () => {
  it('renders three panel run view and supports run selection', async () => {
    const user = userEvent.setup()
    let selectedRunId = 'run-100'
    const selected: string[] = []

    render(
      <RunWorkspace
        runs={runs}
        loading={false}
        selectedRunId={selectedRunId}
        timelineEvents={timeline}
        selectedEventIndex={0}
        selectedEvent={timeline[0]}
        verbosity="normal"
        onPauseRun={async () => undefined}
        onResumeRun={async () => undefined}
        onStopRun={async () => undefined}
        onStartRun={async () => undefined}
        onSetVerbosity={() => undefined}
        onForkFromEvent={async () => undefined}
        onSelectEvent={() => undefined}
        onSelectRun={(runId) => {
          selected.push(runId)
          selectedRunId = runId
        }}
        currentRunCostUsd={0.47}
      />,
    )

    expect(screen.getByRole('heading', { name: /Run Detail/i })).toBeInTheDocument()
    expect(screen.getByText(/Started literature phase/i)).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /Artifacts/i })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /run-101/i }))
    expect(selected).toContain('run-101')
  })

  it('fires run control actions for selected run', async () => {
    const user = userEvent.setup()
    const onPauseRun = vi.fn(async () => undefined)
    const onResumeRun = vi.fn(async () => undefined)
    const onStopRun = vi.fn(async () => undefined)

    render(
      <RunWorkspace
        runs={runs}
        loading={false}
        selectedRunId="run-100"
        timelineEvents={timeline}
        selectedEventIndex={0}
        selectedEvent={timeline[0]}
        verbosity="normal"
        onPauseRun={onPauseRun}
        onResumeRun={onResumeRun}
        onStopRun={onStopRun}
        onStartRun={async () => undefined}
        onSetVerbosity={() => undefined}
        onForkFromEvent={async () => undefined}
        onSelectEvent={() => undefined}
        onSelectRun={() => undefined}
        currentRunCostUsd={0.47}
      />,
    )

    await user.click(screen.getByRole('button', { name: /Pause/i }))
    await user.click(screen.getByRole('button', { name: /Resume/i }))
    await user.click(screen.getByRole('button', { name: /^Stop$/i }))

    expect(onPauseRun).toHaveBeenCalledWith('run-100')
    expect(onResumeRun).toHaveBeenCalledWith('run-100')
    expect(onStopRun).toHaveBeenCalledWith('run-100')
  })

  it('supports verbosity changes and rerun from selected event', async () => {
    const user = userEvent.setup()
    const onSetVerbosity = vi.fn()
    const onForkFromEvent = vi.fn(async () => undefined)

    render(
      <RunWorkspace
        runs={runs}
        loading={false}
        selectedRunId="run-100"
        timelineEvents={timeline}
        selectedEventIndex={0}
        selectedEvent={timeline[0]}
        verbosity="normal"
        onPauseRun={async () => undefined}
        onResumeRun={async () => undefined}
        onStopRun={async () => undefined}
        onStartRun={async () => undefined}
        onSetVerbosity={onSetVerbosity}
        onForkFromEvent={onForkFromEvent}
        onSelectEvent={() => undefined}
        onSelectRun={() => undefined}
        currentRunCostUsd={0.47}
      />,
    )

    await user.selectOptions(screen.getByLabelText(/Verbosity/i), 'debug')
    await user.click(screen.getByRole('button', { name: /Re-run from here/i }))

    expect(onSetVerbosity).toHaveBeenCalledWith('debug')
    expect(onForkFromEvent).toHaveBeenCalledWith(0)
  })
})
