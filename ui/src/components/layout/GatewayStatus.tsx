type GatewayStatusProps = {
  status: 'connected' | 'reconnecting' | 'disconnected'
}

export function GatewayStatus({ status }: GatewayStatusProps) {
  return (
    <>
      <header className="top-bar">
        <h1>OpenEinstein Control UI</h1>
        <p>Gateway: {status}</p>
      </header>
      {status === 'reconnecting' && (
        <div className="reconnect-banner">Reconnecting to gateway...</div>
      )}
    </>
  )
}
