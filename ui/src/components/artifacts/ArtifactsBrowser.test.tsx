import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'

import type { ArtifactRecord } from '../../types/api'
import { ArtifactsBrowser } from './ArtifactsBrowser'

const artifacts: ArtifactRecord[] = [
  {
    run_id: 'run-1',
    name: 'Paper Pack',
    path: '.openeinstein/exports/run-1-paper-pack.zip',
    attached_at: '2026-03-01T00:00:00Z',
  },
  {
    run_id: 'run-1',
    name: 'Summary CSV',
    path: '.openeinstein/exports/summary.csv',
    attached_at: '2026-03-01T00:00:00Z',
  },
]

describe('ArtifactsBrowser', () => {
  it('renders artifacts and dispatches selection + export actions', async () => {
    const user = userEvent.setup()
    const onSelectArtifact = vi.fn(async () => undefined)
    const onExportRun = vi.fn(async () => undefined)

    render(
      <ArtifactsBrowser
        runId="run-1"
        artifacts={artifacts}
        selectedArtifactPath={artifacts[0].path}
        previewText="Preview"
        onSelectArtifact={onSelectArtifact}
        onExportRun={onExportRun}
      />,
    )

    expect(screen.getByRole('heading', { name: /Artifacts/i })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /Summary CSV/i }))
    await user.click(screen.getByRole('button', { name: /Export Paper Pack/i }))

    expect(onSelectArtifact).toHaveBeenCalledWith(artifacts[1].path)
    expect(onExportRun).toHaveBeenCalledTimes(1)
  })
})
