import { useState } from 'react'

import type { ConfigValidationResponse, DashboardSettings } from '../../types/api'

type SettingsPanelProps = {
  initialSettings: DashboardSettings
  onSave: (settings: DashboardSettings) => Promise<ConfigValidationResponse>
  onCheckRemote?: (origin: string) => Promise<{ allowed: boolean; message: string }>
  onTestWebhook?: (url: string) => Promise<{ ok: boolean; message: string }>
  onTestEmail?: (email: string) => Promise<{ ok: boolean; message: string }>
}

export function SettingsPanel({
  initialSettings,
  onSave,
  onCheckRemote,
  onTestWebhook,
  onTestEmail,
}: SettingsPanelProps) {
  const [sessionTimeout, setSessionTimeout] = useState(String(initialSettings.session_timeout_minutes))
  const [notificationsEnabled, setNotificationsEnabled] = useState(initialSettings.notifications_enabled)
  const [allowInsecureRemote, setAllowInsecureRemote] = useState(initialSettings.allow_insecure_remote)
  const [message, setMessage] = useState('')
  const [remoteOrigin, setRemoteOrigin] = useState('')
  const [webhookUrl, setWebhookUrl] = useState('')
  const [emailTarget, setEmailTarget] = useState('')
  const [integrationMessage, setIntegrationMessage] = useState('')

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

      <hr />
      <h3>Remote Safety</h3>
      <label>
        Remote origin
        <input
          aria-label="Remote origin"
          type="text"
          value={remoteOrigin}
          onChange={(event) => setRemoteOrigin(event.target.value)}
        />
      </label>
      <button
        type="button"
        onClick={async () => {
          if (!onCheckRemote) {
            return
          }
          const result = await onCheckRemote(remoteOrigin)
          setIntegrationMessage(result.message)
        }}
      >
        Check remote safety
      </button>

      <h3>Notifications</h3>
      <label>
        Webhook URL
        <input
          aria-label="Webhook URL"
          type="text"
          value={webhookUrl}
          onChange={(event) => setWebhookUrl(event.target.value)}
        />
      </label>
      <button
        type="button"
        onClick={async () => {
          if (!onTestWebhook) {
            return
          }
          const result = await onTestWebhook(webhookUrl)
          setIntegrationMessage(result.message)
        }}
      >
        Test webhook
      </button>

      <label>
        Email target
        <input
          aria-label="Email target"
          type="text"
          value={emailTarget}
          onChange={(event) => setEmailTarget(event.target.value)}
        />
      </label>
      <button
        type="button"
        onClick={async () => {
          if (!onTestEmail) {
            return
          }
          const result = await onTestEmail(emailTarget)
          setIntegrationMessage(result.message)
        }}
      >
        Test email
      </button>
      {integrationMessage && <p>{integrationMessage}</p>}
    </section>
  )
}
