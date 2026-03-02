type LayoutPreset = 'balanced' | 'focus_timeline' | 'focus_details'

type LayoutCustomizerProps = {
  panelLayout: LayoutPreset
  compactNav: boolean
  onChangePanelLayout: (layout: LayoutPreset) => void
  onToggleCompactNav: (value: boolean) => void
}

export function LayoutCustomizer({
  panelLayout,
  compactNav,
  onChangePanelLayout,
  onToggleCompactNav,
}: LayoutCustomizerProps) {
  return (
    <section className="layout-customizer">
      <h2>Layout Customization</h2>
      <p>Persist per-device display preferences for run monitoring.</p>
      <fieldset>
        <legend>Run panel layout</legend>
        <label>
          <input
            type="radio"
            name="panel-layout"
            checked={panelLayout === 'balanced'}
            onChange={() => onChangePanelLayout('balanced')}
          />
          Balanced
        </label>
        <label>
          <input
            type="radio"
            name="panel-layout"
            checked={panelLayout === 'focus_timeline'}
            onChange={() => onChangePanelLayout('focus_timeline')}
          />
          Focus timeline
        </label>
        <label>
          <input
            type="radio"
            name="panel-layout"
            checked={panelLayout === 'focus_details'}
            onChange={() => onChangePanelLayout('focus_details')}
          />
          Focus details
        </label>
      </fieldset>
      <label>
        <input
          type="checkbox"
          checked={compactNav}
          onChange={(event) => onToggleCompactNav(event.target.checked)}
        />
        Compact navigation labels
      </label>
    </section>
  )
}
