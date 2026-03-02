import { render, screen } from '@testing-library/react'

import App from './App'

describe('App mount', () => {
  it('renders the control UI heading', async () => {
    render(<App />)
    expect(
      await screen.findByRole('heading', { name: /OpenEinstein Control UI/i }),
    ).toBeInTheDocument()
  })
})
