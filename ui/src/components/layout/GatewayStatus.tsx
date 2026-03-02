type GatewayStatusProps = {
  status: 'connected' | 'reconnecting' | 'disconnected'
  costTodayUsd: number
  unreadNotifications: number
  onToggleNotifications: () => void
  onOpenCommandPalette?: () => void
}

export function GatewayStatus({
  status,
  costTodayUsd,
  unreadNotifications,
  onToggleNotifications,
  onOpenCommandPalette,
}: GatewayStatusProps) {
  return (
    <>
      <header className="top-bar">
        <h1>OpenEinstein Control UI</h1>
        <div className="top-bar-meta">
          <p>Gateway: {status}</p>
          <p>Cost today: ${costTodayUsd.toFixed(2)}</p>
          {onOpenCommandPalette && (
            <button type="button" onClick={onOpenCommandPalette}>
              Command Palette
            </button>
          )}
          <button type="button" onClick={onToggleNotifications}>
            Notifications ({unreadNotifications})
          </button>
        </div>
      </header>
      {status === 'reconnecting' && (
        <div className="reconnect-banner">Reconnecting to gateway...</div>
      )}
    </>
  )
}
