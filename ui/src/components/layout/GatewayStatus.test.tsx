import { render, screen } from '@testing-library/react'

import { GatewayStatus } from './GatewayStatus'

describe('GatewayStatus', () => {
  it('renders reconnect banner when status is reconnecting', () => {
    render(<GatewayStatus status="reconnecting" />)
    expect(screen.getByText(/Gateway: reconnecting/i)).toBeInTheDocument()
    expect(screen.getByText(/Reconnecting to gateway/i)).toBeInTheDocument()
  })
})
