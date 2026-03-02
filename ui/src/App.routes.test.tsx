import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import App from './App'

describe('App routing and shell', () => {
  it('renders shell chrome and navigates to settings, approvals, artifacts, and tools', async () => {
    render(<App />)
    expect(await screen.findByRole('heading', { name: /OpenEinstein Control UI/i })).toBeInTheDocument()
    expect(screen.getByText(/Gateway:/i)).toBeInTheDocument()
    await waitFor(() => expect(screen.getByText(/No active runs/i)).toBeInTheDocument())

    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: /Approvals/i }))
    expect(screen.getByRole('heading', { name: /Approvals/i })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /Artifacts/i }))
    expect(screen.getByRole('heading', { name: /Artifacts/i })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /Tools/i }))
    expect(screen.getByRole('heading', { name: /Tools/i })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /Settings/i }))
    expect(screen.getByRole('heading', { name: /Settings/i })).toBeInTheDocument()
  })
})
