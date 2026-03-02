import type { ToolRecord } from '../../types/api'

type ToolsPanelProps = {
  tools: ToolRecord[]
  testResults?: Record<string, string>
  onTestConnection: (toolId: string) => Promise<void>
}

export function ToolsPanel({ tools, testResults = {}, onTestConnection }: ToolsPanelProps) {
  return (
    <section className="tools-panel">
      <h2>Tools</h2>
      {tools.length === 0 ? (
        <p>No tools discovered.</p>
      ) : (
        <ul className="tools-list">
          {tools.map((tool) => (
            <li key={tool.id} className={`tool-card tool-${tool.status}`}>
              <div>
                <strong>{tool.id}</strong>
                <p>Status: {tool.status}</p>
                <p>Latency: {tool.latency_ms ?? 0} ms</p>
                {testResults[tool.id] && <p>{tool.id}: {testResults[tool.id]}</p>}
              </div>
              <button type="button" onClick={() => void onTestConnection(tool.id)}>
                Test {tool.id}
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
