import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'

import type { PendingApproval } from '../../stores/approvals'
import { ApprovalsCenter } from './ApprovalsCenter'

const approvals: PendingApproval[] = [
  {
    approval_id: 'a-2',
    run_id: 'run-22',
    risk: 'low',
    what: 'read-only tool call',
    why: 'fetch metadata',
    action: 'tool.read',
    requested_at: '2026-03-01T00:00:00Z',
  },
  {
    approval_id: 'a-1',
    run_id: 'run-22',
    risk: 'high',
    what: 'shell execution',
    why: 'execute export command',
    action: 'shell_exec',
    requested_at: '2026-03-01T00:01:00Z',
  },
]

describe('ApprovalsCenter', () => {
  it('renders sorted approvals and dispatches decision actions', async () => {
    const user = userEvent.setup()
    const onDecide = vi.fn(async () => undefined)
    const onApproveLowRisk = vi.fn(async () => undefined)

    render(
      <ApprovalsCenter
        approvals={approvals}
        onDecide={onDecide}
        onApproveLowRisk={onApproveLowRisk}
      />,
    )

    const cards = screen.getAllByRole('listitem')
    expect(cards[0]).toHaveTextContent(/shell execution/i)

    await user.click(screen.getByRole('button', { name: /approve all low-risk/i }))
    await user.click(screen.getByRole('button', { name: /approve a-1/i }))
    await user.click(screen.getByRole('button', { name: /deny a-2/i }))

    expect(onApproveLowRisk).toHaveBeenCalledTimes(1)
    expect(onDecide).toHaveBeenNthCalledWith(1, 'a-1', 'approve')
    expect(onDecide).toHaveBeenNthCalledWith(2, 'a-2', 'deny')
  })
})
