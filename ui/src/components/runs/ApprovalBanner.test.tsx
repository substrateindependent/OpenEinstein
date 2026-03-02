import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'

import type { PendingApproval } from '../../stores/approvals'
import { ApprovalBanner } from './ApprovalBanner'

const pending: PendingApproval[] = [
  {
    approval_id: 'a-high',
    run_id: 'run-1',
    risk: 'high',
    what: 'shell command',
    why: 'run latexmk',
    action: 'shell_exec',
    requested_at: '2026-03-01T00:00:00Z',
  },
]

describe('ApprovalBanner', () => {
  it('renders pending approvals and decision actions', async () => {
    const user = userEvent.setup()
    const onDecide = vi.fn(async () => undefined)

    render(<ApprovalBanner pending={pending} onDecide={onDecide} />)
    expect(screen.getByText(/approval required/i)).toBeInTheDocument()
    expect(screen.getByText(/shell command/i)).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /approve a-high/i }))
    expect(onDecide).toHaveBeenCalledWith('a-high', 'approve')
  })
})
