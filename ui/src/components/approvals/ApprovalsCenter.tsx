import type { ApprovalDecision, PendingApproval } from '../../stores/approvals'

type ApprovalsCenterProps = {
  approvals: PendingApproval[]
  onDecide: (approvalId: string, decision: ApprovalDecision) => Promise<void>
  onApproveLowRisk: () => Promise<void>
}

const riskOrder: Record<PendingApproval['risk'], number> = {
  high: 0,
  medium: 1,
  low: 2,
}

function sortByRisk(items: PendingApproval[]): PendingApproval[] {
  return [...items].sort((a, b) => {
    const riskDelta = riskOrder[a.risk] - riskOrder[b.risk]
    if (riskDelta !== 0) {
      return riskDelta
    }
    return a.requested_at.localeCompare(b.requested_at)
  })
}

export function ApprovalsCenter({ approvals, onDecide, onApproveLowRisk }: ApprovalsCenterProps) {
  const sorted = sortByRisk(approvals)

  return (
    <section className="approvals-center">
      <header className="approvals-header">
        <h2>Approvals</h2>
        <button type="button" onClick={() => void onApproveLowRisk()}>
          Approve all low-risk
        </button>
      </header>
      {sorted.length === 0 ? (
        <p>No pending approvals.</p>
      ) : (
        <ul className="approvals-list">
          {sorted.map((approval) => (
            <li key={approval.approval_id} className={`approval-card risk-${approval.risk}`}>
              <div className="approval-copy">
                <p>
                  <strong>{approval.what}</strong>
                </p>
                <p>{approval.why}</p>
                <p>
                  Run: <code>{approval.run_id}</code>
                </p>
                <p>
                  Risk: <strong>{approval.risk}</strong>
                </p>
              </div>
              <div className="approval-actions">
                <button
                  type="button"
                  onClick={() => void onDecide(approval.approval_id, 'approve')}
                  aria-label={`Approve ${approval.approval_id}`}
                >
                  Approve
                </button>
                <button
                  type="button"
                  onClick={() => void onDecide(approval.approval_id, 'deny')}
                  aria-label={`Deny ${approval.approval_id}`}
                >
                  Deny
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
