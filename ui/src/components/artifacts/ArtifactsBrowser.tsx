import type { ArtifactRecord } from '../../types/api'

type ArtifactsBrowserProps = {
  runId: string | null
  artifacts: ArtifactRecord[]
  selectedArtifactPath: string | null
  previewText: string
  downloadUrl?: string
  onSelectArtifact: (artifactPath: string) => Promise<void>
  onExportRun: () => Promise<void>
}

function artifactLabel(path: string): string {
  const pieces = path.split('/')
  return pieces[pieces.length - 1] ?? path
}

export function ArtifactsBrowser({
  runId,
  artifacts,
  selectedArtifactPath,
  previewText,
  downloadUrl,
  onSelectArtifact,
  onExportRun,
}: ArtifactsBrowserProps) {
  return (
    <section className="artifacts-browser">
      <header className="artifacts-header">
        <h2>Artifacts</h2>
        <div className="artifacts-actions">
          <button type="button" onClick={() => void onExportRun()} disabled={!runId}>
            Export Paper Pack
          </button>
          {downloadUrl && (
            <a href={downloadUrl} target="_blank" rel="noreferrer">
              Download Paper Pack
            </a>
          )}
        </div>
      </header>
      <p>
        Run: <code>{runId ?? 'none selected'}</code>
      </p>

      {artifacts.length === 0 ? (
        <p>No artifacts available for this run.</p>
      ) : (
        <ul className="artifact-list">
          {artifacts.map((artifact) => (
            <li key={artifact.path}>
              <button
                type="button"
                onClick={() => void onSelectArtifact(artifact.path)}
                className={artifact.path === selectedArtifactPath ? 'selected-artifact' : ''}
              >
                {artifact.name} ({artifactLabel(artifact.path)})
              </button>
            </li>
          ))}
        </ul>
      )}

      <section className="artifact-preview">
        <h3>Preview</h3>
        <pre>{previewText || 'Select an artifact to preview.'}</pre>
      </section>
    </section>
  )
}
