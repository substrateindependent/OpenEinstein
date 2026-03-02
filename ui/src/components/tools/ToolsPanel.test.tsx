import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'

import type { ToolRecord } from '../../types/api'
import { ToolsPanel } from './ToolsPanel'

const tools: ToolRecord[] = [
  { id: 'sympy', status: 'available', latency_ms: 12 },
  { id: 'scanner', status: 'degraded', latency_ms: 140 },
]

describe('ToolsPanel', () => {
  it('renders tool rows and dispatches test connection action', async () => {
    const user = userEvent.setup()
    const onTestConnection = vi.fn(async () => undefined)

    render(<ToolsPanel tools={tools} onTestConnection={onTestConnection} />)
    expect(screen.getByRole('heading', { name: /Tools/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Test sympy/i })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /Test sympy/i }))
    expect(onTestConnection).toHaveBeenCalledWith('sympy')
  })
})
