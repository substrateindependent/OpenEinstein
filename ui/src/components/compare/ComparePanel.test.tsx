import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'

import type { ComparedRun } from '../../types/api'
import { ComparePanel } from './ComparePanel'

const compared: ComparedRun[] = [
  {
    run_id: 'run-1',
    status: 'running',
    estimated_cost_usd: 2.2,
    confidence: 0.72,
    tags: ['baseline'],
  },
  {
    run_id: 'run-2',
    status: 'failed',
    estimated_cost_usd: 3.1,
    confidence: 0.3,
    tags: ['failed'],
  },
]

describe('ComparePanel', () => {
  it('renders compare output and dispatches tag updates', async () => {
    const user = userEvent.setup()
    const onUpdateTag = vi.fn(async () => undefined)

    render(<ComparePanel comparedRuns={compared} onUpdateTag={onUpdateTag} />)
    expect(screen.getByRole('heading', { name: /Comparison Results/i })).toBeInTheDocument()
    expect(screen.getByText(/Confidence: 0.30/i)).toBeInTheDocument()

    await user.clear(screen.getByLabelText(/Tag run-1/i))
    await user.type(screen.getByLabelText(/Tag run-1/i), 'candidate')
    await user.click(screen.getByRole('button', { name: /Save tag run-1/i }))
    expect(onUpdateTag).toHaveBeenCalledWith('run-1', 'candidate')
  })
})
