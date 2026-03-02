import { createNotificationsStore } from './notifications'

describe('notifications store', () => {
  it('creates notification entries from approval and cost warning events', () => {
    const store = createNotificationsStore()

    store.getState().applyEvent({
      type: 'approval_required',
      payload: { approval_id: 'a-1', what: 'shell_exec' },
    })
    store.getState().applyEvent({
      type: 'cost_update',
      payload: { run_id: 'run-1', budget_percent: 82, estimated_cost_usd: 5.5 },
    })

    expect(store.getState().unreadCount).toBe(2)
    expect(store.getState().items[0]?.message).toMatch(/approval/i)
    expect(store.getState().items[1]?.message).toMatch(/80%/i)
  })
})
