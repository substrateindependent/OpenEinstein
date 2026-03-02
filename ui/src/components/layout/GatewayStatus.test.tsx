import { render, screen } from '@testing-library/react'
import { vi } from 'vitest'

import { GatewayStatus } from './GatewayStatus'

describe('GatewayStatus', () => {
  it('renders reconnect banner when status is reconnecting', () => {
    render(
      <GatewayStatus
        status="reconnecting"
        costTodayUsd={2.14}
        unreadNotifications={3}
        onToggleNotifications={vi.fn()}
        onOpenCommandPalette={vi.fn()}
      />,
    )
    expect(screen.getByText(/Gateway: reconnecting/i)).toBeInTheDocument()
    expect(screen.getByText(/Cost today: \$2.14/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Command Palette/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Notifications \(3\)/i })).toBeInTheDocument()
    expect(screen.getByText(/Reconnecting to gateway/i)).toBeInTheDocument()
  })
})
