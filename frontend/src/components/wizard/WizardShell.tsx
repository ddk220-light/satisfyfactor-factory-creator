import { useState } from "react"
import type { UserPreferences, AnalyzeResult, LocationCandidate, FactoryResult } from "../../types/plan"
import PreferencesStep from "./PreferencesStep"
import RecipeStep from "./RecipeStep"
import LocationStep from "./LocationStep"
import Dashboard from "../dashboard/Dashboard"

type WizardStep = "preferences" | "recipes" | "locations" | "dashboard"

interface WizardState {
  preferences: UserPreferences | null
  analysis: AnalyzeResult | null
  selectedLocations: Record<string, LocationCandidate> | null
  results: FactoryResult[] | null
}

export default function WizardShell() {
  const [step, setStep] = useState<WizardStep>("preferences")
  const [state, setState] = useState<WizardState>({
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
      {step === "recipes" && state.preferences && (
        <RecipeStep
          preferences={state.preferences}
          onComplete={(analysis) => {
            setState(s => ({ ...s, analysis }))
            setStep("locations")
          }}
          onBack={() => setStep("preferences")}
        />
      )}
      {step === "locations" && state.preferences && state.analysis && (
        <LocationStep
          preferences={state.preferences}
          analysis={state.analysis}
          onComplete={(selected) => {
            setState(s => ({ ...s, selectedLocations: selected }))
            setStep("dashboard")
          }}
          onBack={() => setStep("recipes")}
        />
      )}
      {step === "dashboard" && state.preferences && state.analysis && state.selectedLocations && (
        <Dashboard
          preferences={state.preferences}
          analysis={state.analysis}
          selectedLocations={state.selectedLocations}
        />
      )}
    </div>
  )
}
