import { createCostStore } from './cost'

describe('cost store', () => {
  it('applies cost_update events and tracks run + today totals', () => {
    const store = createCostStore()

    store.getState().applyEvent({
      type: 'cost_update',
      payload: {
        run_id: 'run-1',
        estimated_cost_usd: 1.25,
        token_count: 1000,
        budget_percent: 25,
      },
    })
    store.getState().applyEvent({
      type: 'cost_update',
      payload: {
        run_id: 'run-2',
        estimated_cost_usd: 2.5,
        token_count: 2000,
        budget_percent: 50,
      },
    })

    expect(store.getState().todayCostUsd).toBe(3.75)
    expect(store.getState().runCosts['run-1']?.estimated_cost_usd).toBe(1.25)
    expect(store.getState().runCosts['run-2']?.token_count).toBe(2000)
  })
})
