import { useMemo, useState } from 'react'

import type { ComparedRun } from '../../types/api'

type ComparePanelProps = {
  comparedRuns: ComparedRun[]
  onUpdateTag: (runId: string, tag: string) => Promise<void>
}

export function ComparePanel({ comparedRuns, onUpdateTag }: ComparePanelProps) {
  const [tagInputs, setTagInputs] = useState<Record<string, string>>({})
  const minConfidence = useMemo(() => {
    if (comparedRuns.length === 0) {
      return 0
    }
    return comparedRuns.reduce((min, run) => Math.min(min, run.confidence), 1)
  }, [comparedRuns])

  return (
    <section className="compare-panel">
      <h3>Comparison Results</h3>
      <p>Confidence: {minConfidence.toFixed(2)}</p>

      {comparedRuns.length === 0 ? (
        <p>Select runs and execute compare.</p>
      ) : (
        <table className="compare-table">
          <thead>
            <tr>
              <th>Run</th>
              <th>Status</th>
              <th>Cost</th>
              <th>Confidence</th>
              <th>Tag</th>
              <th>Links</th>
            </tr>
          </thead>
          <tbody>
            {comparedRuns.map((run) => (
              <tr key={run.run_id}>
                <td>{run.run_id}</td>
                <td>{run.status}</td>
                <td>${run.estimated_cost_usd.toFixed(2)}</td>
                <td>{run.confidence.toFixed(2)}</td>
                <td>
                  <label>
                    <span className="sr-only">Tag {run.run_id}</span>
                    <input
                      aria-label={`Tag ${run.run_id}`}
                      value={tagInputs[run.run_id] ?? run.tags[0] ?? ''}
                      onChange={(event) =>
                        setTagInputs((state) => ({ ...state, [run.run_id]: event.target.value }))
                      }
                    />
                  </label>
                  <button
                    type="button"
                    onClick={() =>
                      void onUpdateTag(run.run_id, tagInputs[run.run_id] ?? run.tags[0] ?? '')
                    }
                  >
                    Save tag {run.run_id}
                  </button>
                </td>
                <td>
                  <a href={`/api/v1/runs/${run.run_id}/events`} target="_blank" rel="noreferrer">
                    Events
                  </a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  )
}
