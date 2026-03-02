import type { ApprovalDecision, PendingApproval } from '../../stores/approvals'

type ApprovalBannerProps = {
  pending: PendingApproval[]
  onDecide: (approvalId: string, decision: ApprovalDecision) => Promise<void>
}

export function ApprovalBanner({ pending, onDecide }: ApprovalBannerProps) {
  if (pending.length === 0) {
    return null
  }

  return (
    <section className="approval-banner" role="region" aria-label="Approval required">
      <header className="approval-banner-header">
        <h2>Approval Required</h2>
        <p>{pending.length} pending decision(s)</p>
      </header>
      <ul className="approval-banner-list">
        {pending.map((approval) => (
          <li key={approval.approval_id} className={`approval-pill risk-${approval.risk}`}>
            <div>
              <strong>{approval.what}</strong>
              <p>{approval.why}</p>
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
    </section>
  )
}
