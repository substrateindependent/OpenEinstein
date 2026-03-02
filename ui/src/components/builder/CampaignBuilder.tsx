import type { PackRecord, PackSchemaResponse } from '../../types/api'

type CampaignBuilderProps = {
  packs: PackRecord[]
  selectedPackId: string
  schema: PackSchemaResponse | null
  values: Record<string, string>
  submitMessage: string
  onSelectPack: (packId: string) => void
  onUpdateValue: (name: string, value: string) => void
  onSubmit: () => Promise<void>
}

export function CampaignBuilder({
  packs,
  selectedPackId,
  schema,
  values,
  submitMessage,
  onSelectPack,
  onUpdateValue,
  onSubmit,
}: CampaignBuilderProps) {
  return (
    <section className="campaign-builder">
      <h2>Campaign Builder</h2>
      <p>Generate a run request from pack-provided schema fields.</p>
      <label>
        Campaign pack
        <select
          aria-label="Campaign pack"
          value={selectedPackId}
          onChange={(event) => onSelectPack(event.target.value)}
        >
          {packs.length === 0 ? <option value="">No packs installed</option> : null}
          {packs.map((pack) => (
            <option key={pack.id} value={pack.id}>
              {pack.id}
            </option>
          ))}
        </select>
      </label>
      {schema ? (
        <div className="builder-schema">
          <h3>{schema.title}</h3>
          {schema.description ? <p>{schema.description}</p> : null}
          {schema.fields.map((field) => (
            <label key={field.name}>
              {field.label}
              <input
                aria-label={field.label}
                type={field.type === 'number' ? 'number' : 'text'}
                value={values[field.name] ?? ''}
                onChange={(event) => onUpdateValue(field.name, event.target.value)}
              />
            </label>
          ))}
          <button type="button" onClick={() => void onSubmit()}>
            Start run from builder
          </button>
          {submitMessage ? <p>{submitMessage}</p> : null}
        </div>
      ) : (
        <p>Select a pack to load schema fields.</p>
      )}
    </section>
  )
}
