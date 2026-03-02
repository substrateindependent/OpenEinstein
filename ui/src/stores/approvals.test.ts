import { createApprovalsStore } from './approvals'

describe('approvals store', () => {
  it('sorts pending approvals by risk and resolves decisions', () => {
    const store = createApprovalsStore()

    store.getState().applyEvent({
      type: 'approval_required',
      payload: {
        approval_id: 'a-low',
        run_id: 'run-1',
        risk: 'low',
        what: 'read arxiv',
        why: 'literature query',
      },
    })
    store.getState().applyEvent({
      type: 'approval_required',
      payload: {
        approval_id: 'a-high',
        run_id: 'run-1',
        risk: 'high',
        what: 'shell exec',
        why: 'run external command',
      },
    })

    const sorted = store.getState().pendingSorted
    expect(sorted[0]?.approval_id).toBe('a-high')

    store.getState().applyEvent({
      type: 'approval_resolved',
      payload: { approval_id: 'a-high', decision: 'approve' },
    })
    expect(store.getState().pendingSorted.map((item) => item.approval_id)).toEqual(['a-low'])
  })
})
