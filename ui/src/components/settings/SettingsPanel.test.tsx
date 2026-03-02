import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'

import { SettingsPanel } from './SettingsPanel'

describe('SettingsPanel', () => {
  it('validates session timeout and dispatches save callback', async () => {
    const user = userEvent.setup()
    const onSave = vi.fn(async () => ({ valid: true, errors: [] }))

    render(
      <SettingsPanel
        initialSettings={{
          session_timeout_minutes: 480,
          notifications_enabled: true,
          allow_insecure_remote: false,
        }}
        onSave={onSave}
      />,
    )

    await user.clear(screen.getByLabelText(/Session timeout \(minutes\)/i))
    await user.type(screen.getByLabelText(/Session timeout \(minutes\)/i), '0')
    await user.click(screen.getByRole('button', { name: /Save settings/i }))
    expect(screen.getByText(/must be greater than 0/i)).toBeInTheDocument()

    await user.clear(screen.getByLabelText(/Session timeout \(minutes\)/i))
    await user.type(screen.getByLabelText(/Session timeout \(minutes\)/i), '120')
    await user.click(screen.getByRole('button', { name: /Save settings/i }))
    expect(onSave).toHaveBeenCalled()
  })
})
