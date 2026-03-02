import { useMemo, useState } from 'react'

export type PaletteCommand = {
  id: string
  label: string
  run: () => Promise<void> | void
}

type CommandPaletteProps = {
  open: boolean
  commands: PaletteCommand[]
  onClose: () => void
  onRunNaturalLanguage?: (command: string) => Promise<string | void>
}

export function CommandPalette({ open, commands, onClose, onRunNaturalLanguage }: CommandPaletteProps) {
  const [query, setQuery] = useState('')
  const [nlMode, setNlMode] = useState(false)
  const [nlCommand, setNlCommand] = useState('')
  const [nlMessage, setNlMessage] = useState('')

  const filtered = useMemo(() => {
    const lowered = query.trim().toLowerCase()
    if (!lowered) {
      return commands
    }
    return commands.filter((command) => command.label.toLowerCase().includes(lowered))
  }, [commands, query])

  if (!open) {
    return null
  }

  return (
    <section className="command-palette" role="dialog" aria-label="Command palette">
      <div className="command-palette-header">
        <h2>Command Palette</h2>
        <button type="button" onClick={onClose}>
          Close
        </button>
      </div>
      <input
        aria-label="Natural language mode"
        type="checkbox"
        checked={nlMode}
        onChange={(event) => setNlMode(event.target.checked)}
      />
      {nlMode ? (
        <div className="nl-command-form">
          <input
            aria-label="Natural language command"
            type="text"
            value={nlCommand}
            onChange={(event) => setNlCommand(event.target.value)}
            placeholder="e.g. open settings or start run"
          />
          <button
            type="button"
            onClick={async () => {
              if (!onRunNaturalLanguage || !nlCommand.trim()) {
                return
              }
              const message = await onRunNaturalLanguage(nlCommand.trim())
              setNlMessage(message ?? '')
              setNlCommand('')
              onClose()
            }}
          >
            Run NL command
          </button>
          {nlMessage ? <p>{nlMessage}</p> : null}
        </div>
      ) : (
        <>
          <input
            aria-label="Command search"
            type="text"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Type a command..."
          />
          <ul className="command-list">
            {filtered.map((command) => (
              <li key={command.id}>
                <button
                  type="button"
                  onClick={async () => {
                    await command.run()
                    setQuery('')
                    onClose()
                  }}
                >
                  {command.label}
                </button>
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  )
}
