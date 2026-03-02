import { useState } from 'react'

type RunWizardProps = {
  onStart: () => Promise<void>
}

const TOTAL_STEPS = 4

export function RunWizard({ onStart }: RunWizardProps) {
  const [step, setStep] = useState(1)
  const [campaignPath, setCampaignPath] = useState('campaigns/sample.yaml')
  const [advanced, setAdvanced] = useState(false)

  function next() {
    setStep((current) => Math.min(TOTAL_STEPS, current + 1))
  }

  function back() {
    setStep((current) => Math.max(1, current - 1))
  }

  return (
    <section className="wizard">
      <h2>Step {step}</h2>
      {step === 1 && (
        <div>
          <p>Select campaign pack</p>
          <input
            aria-label="Campaign path"
            value={campaignPath}
            onChange={(event) => setCampaignPath(event.target.value)}
          />
        </div>
      )}
      {step === 2 && (
        <div>
          <p>Configure parameters</p>
          <label>
            <input
              type="checkbox"
              checked={advanced}
              onChange={(event) => setAdvanced(event.target.checked)}
            />
            Show advanced options
          </label>
        </div>
      )}
      {step === 3 && (
        <div>
          <p>Review preflight</p>
          <p>Campaign: {campaignPath}</p>
          <p>Advanced: {advanced ? 'enabled' : 'disabled'}</p>
        </div>
      )}
      {step === 4 && (
        <div>
          <p>Ready to start</p>
          <button type="button" onClick={() => void onStart()}>
            Start Run
          </button>
        </div>
      )}

      <div className="wizard-actions">
        <button type="button" onClick={back} disabled={step === 1}>
          Back
        </button>
        <button type="button" onClick={next} disabled={step === TOTAL_STEPS}>
          Next
        </button>
      </div>
    </section>
  )
}
