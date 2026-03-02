import { createRunsStore } from './runs'

describe('runs store', () => {
  it('hydrates runs, applies run_state updates, and appends timeline events', () => {
    const store = createRunsStore()
    store.getState().setRuns([
      { run_id: 'run-1', status: 'running', started_at: '2026-03-01T00:00:00Z' },
    ])

    store.getState().applyEvent({
      type: 'run_state',
      payload: { run_id: 'run-1', status: 'stopped' },
    })

    expect(store.getState().runs[0]?.status).toBe('stopped')
    expect(store.getState().activeSummary).toMatch(/run-1/i)
    expect(store.getState().selectedRunId).toBe('run-1')

    store.getState().applyEvent({
      type: 'run_event',
      payload: {
        run_id: 'run-1',
        summary: 'Tool call complete',
        ts: '2026-03-01T00:00:01Z',
      },
    })
    expect(store.getState().timelineByRun['run-1']?.[0]?.summary).toMatch(/tool call/i)
  })
})
