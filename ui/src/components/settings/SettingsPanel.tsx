import { useState } from 'react'

import type { ConfigValidationResponse, DashboardSettings } from '../../types/api'

type SettingsPanelProps = {
  initialSettings: DashboardSettings
  onSave: (settings: DashboardSettings) => Promise<ConfigValidationResponse>
}

export function SettingsPanel({ initialSettings, onSave }: SettingsPanelProps) {
  const [sessionTimeout, setSessionTimeout] = useState(String(initialSettings.session_timeout_minutes))
  const [notificationsEnabled, setNotificationsEnabled] = useState(initialSettings.notifications_enabled)
  const [allowInsecureRemote, setAllowInsecureRemote] = useState(initialSettings.allow_insecure_remote)
  const [message, setMessage] = useState('')

  async function handleSave() {
    const timeout = Number(sessionTimeout)
    if (!Number.isFinite(timeout) || timeout <= 0) {
      setMessage('Session timeout must be greater than 0.')
      return
    }

    const result = await onSave({
      session_timeout_minutes: timeout,
      notifications_enabled: notificationsEnabled,
      allow_insecure_remote: allowInsecureRemote,
    })
    if (result.valid) {
      setMessage('Settings validated successfully.')
      return
    }
    setMessage(result.errors.join(', ') || 'Settings validation failed.')
  }

  return (
    <section className="settings-panel">
      <h2>Settings</h2>
      <label>
        Session timeout (minutes)
        <input
          aria-label="Session timeout (minutes)"
          type="number"
          min={1}
          value={sessionTimeout}
          onChange={(event) => setSessionTimeout(event.target.value)}
        />
      </label>
      <label>
        <input
          type="checkbox"
          checked={notificationsEnabled}
          onChange={(event) => setNotificationsEnabled(event.target.checked)}
        />
        Enable notifications
      </label>
      <label>
        <input
          type="checkbox"
          checked={allowInsecureRemote}
          onChange={(event) => setAllowInsecureRemote(event.target.checked)}
        />
        Allow insecure remote access
      </label>
      {allowInsecureRemote && (
        <p className="settings-warning">
          Insecure remote mode is dangerous. Keep this disabled unless you use a secure tunnel.
        </p>
      )}
      <button type="button" onClick={() => void handleSave()}>
        Save settings
      </button>
      {message && <p>{message}</p>}
    </section>
  )
}
