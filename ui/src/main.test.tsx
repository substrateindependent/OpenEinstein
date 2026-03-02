import { render, screen } from '@testing-library/react'

import App from './App'

describe('App mount', () => {
  it('renders the control UI heading', () => {
    render(<App />)
    expect(
      screen.getByRole('heading', { name: /OpenEinstein Control UI/i }),
    ).toBeInTheDocument()
  })
})
