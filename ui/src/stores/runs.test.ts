import { createRunsStore } from './runs'

describe('runs store', () => {
  it('hydrates runs and applies ws run_state updates', () => {
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
  })
})
