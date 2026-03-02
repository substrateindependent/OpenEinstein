import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'

import { RunWizard } from './RunWizard'

describe('RunWizard', () => {
  it('progresses through steps and triggers start callback', async () => {
    const user = userEvent.setup()
    const onStart = vi.fn(async () => undefined)

    render(<RunWizard onStart={onStart} />)

    expect(screen.getByRole('heading', { name: /Step 1/i })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /Next/i }))
    expect(screen.getByRole('heading', { name: /Step 2/i })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /Next/i }))
    expect(screen.getByRole('heading', { name: /Step 3/i })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /Next/i }))
    expect(screen.getByRole('heading', { name: /Step 4/i })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /Start Run/i }))
    expect(onStart).toHaveBeenCalledTimes(1)
  })
})
