import { useState } from "react"
import type { UserPreferences, AnalyzeResult, LocationCandidate, FactoryResult } from "../../types/plan"
import PreferencesStep from "./PreferencesStep"

type WizardStep = "preferences" | "recipes" | "locations" | "dashboard"

interface WizardState {
  preferences: UserPreferences | null
  analysis: AnalyzeResult | null
  selectedLocations: Record<string, LocationCandidate> | null
  results: FactoryResult[] | null
}

export default function WizardShell() {
  const [step, setStep] = useState<WizardStep>("preferences")
  const [_state, setState] = useState<WizardState>({
    preferences: null, analysis: null, selectedLocations: null, results: null,
  })

  return (
    <div>
      {/* Step indicator */}
      <nav style={{ display: "flex", gap: 16, padding: 16, borderBottom: "1px solid #333" }}>
        {(["preferences", "recipes", "locations", "dashboard"] as const).map((s, i) => (
          <span key={s} style={{
            color: s === step ? "#fff" : "#666",
            fontWeight: s === step ? "bold" : "normal",
          }}>
            {i + 1}. {s.charAt(0).toUpperCase() + s.slice(1)}
          </span>
        ))}
      </nav>

      {step === "preferences" && (
        <PreferencesStep onComplete={(prefs) => {
          setState(s => ({ ...s, preferences: prefs }))
          setStep("recipes")
        }} />
      )}
      {step === "recipes" && <div style={{ padding: 16 }}>Recipe Selection (Task 13)</div>}
      {step === "locations" && <div style={{ padding: 16 }}>Location Selection (Task 14)</div>}
      {step === "dashboard" && <div style={{ padding: 16 }}>Dashboard (Tasks 15-18)</div>}
    </div>
  )
}
