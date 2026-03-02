import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'

import { CommandPalette } from './CommandPalette'

describe('CommandPalette', () => {
  it('filters commands and dispatches selected action', async () => {
    const user = userEvent.setup()
    const onClose = vi.fn()
    const onExecuteSettings = vi.fn(async () => undefined)
    const onExecuteRun = vi.fn(async () => undefined)

    render(
      <CommandPalette
        open
        onClose={onClose}
        commands={[
          { id: 'go-settings', label: 'Open Settings', run: onExecuteSettings },
          { id: 'start-run', label: 'Start Sample Run', run: onExecuteRun },
        ]}
      />,
    )

    await user.type(screen.getByLabelText(/Command search/i), 'settings')
    await user.click(screen.getByRole('button', { name: /Open Settings/i }))

    expect(onExecuteSettings).toHaveBeenCalledTimes(1)
    expect(onClose).toHaveBeenCalledTimes(1)
    expect(onExecuteRun).not.toHaveBeenCalled()
  })
})
