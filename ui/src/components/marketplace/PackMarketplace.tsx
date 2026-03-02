import type { PackRecord } from '../../types/api'

type PackMarketplaceProps = {
  packs: PackRecord[]
  installMessage: string
  onInstall: (packId: string) => Promise<void>
}

export function PackMarketplace({ packs, installMessage, onInstall }: PackMarketplaceProps) {
  return (
    <section className="pack-marketplace">
      <h2>Pack Marketplace</h2>
      <p>Install curated packs with trust and scan visibility.</p>
      {packs.length === 0 ? (
        <p>No marketplace packs available.</p>
      ) : (
        <ul className="marketplace-list">
          {packs.map((pack) => (
            <li key={pack.id} className="marketplace-card">
              <div>
                <strong>{pack.name ?? pack.id}</strong>
                <p>{pack.description ?? 'No description available.'}</p>
                <p>Trust tier: {pack.trust_tier ?? 'unknown'}</p>
              </div>
              <button type="button" onClick={() => void onInstall(pack.id)}>
                {pack.installed ? 'Reinstall' : 'Install'}
              </button>
            </li>
          ))}
        </ul>
      )}
      {installMessage ? <p>{installMessage}</p> : null}
    </section>
  )
}
