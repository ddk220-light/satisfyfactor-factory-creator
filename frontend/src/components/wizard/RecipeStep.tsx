import { useState, useEffect } from "react"
import type { UserPreferences, AnalyzeResult } from "../../types/plan"
import { usePlanAPI } from "../../hooks/usePlanAPI"
import RecipeDAG from "../recipes/RecipeDAG"

interface Props {
  preferences: UserPreferences
  onComplete: (analysis: AnalyzeResult) => void
  onBack: () => void
}

export default function RecipeStep({ preferences, onComplete, onBack }: Props) {
  const api = usePlanAPI()
  const [analysis, setAnalysis] = useState<AnalyzeResult | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    api.analyze(
      preferences.targetItem,
      preferences.targetRate,
      preferences.excludedRecipes,
      preferences.maxFactories
    )
      .then(result => { setAnalysis(result); setLoading(false) })
      .catch(err => { setError(err.message); setLoading(false) })
  }, [preferences.targetItem, preferences.targetRate, preferences.maxFactories])

  if (loading) return <div style={{ padding: 24, color: "#999" }}>Analyzing production chain...</div>
  if (error) return <div style={{ padding: 24, color: "#f87171" }}>Error: {error}</div>
  if (!analysis) return null

  return (
    <div style={{ display: "flex", minHeight: "calc(100vh - 60px)" }}>
      {/* Main: DAG */}
      <div style={{ flex: 1, padding: 24, overflow: "auto" }}>
        <h2 style={{ color: "#fff", marginBottom: 16 }}>
          Production Chain: {preferences.targetItem}
        </h2>
        <p style={{ color: "#999", marginBottom: 16 }}>
          {analysis.dag.length} recipe steps identified
        </p>
        <div style={{ overflow: "auto" }}>
          <RecipeDAG dag={analysis.dag} />
        </div>
        <div style={{ marginTop: 24, display: "flex", gap: 12 }}>
          <button onClick={onBack}
            style={{ padding: "8px 20px", background: "#333", color: "#ccc",
              border: "1px solid #555", borderRadius: 4, cursor: "pointer" }}>
            &larr; Back
          </button>
          <button onClick={() => onComplete(analysis)}
            style={{ padding: "8px 20px", background: "#2563eb", color: "#fff",
              border: "none", borderRadius: 4, cursor: "pointer", fontSize: 16 }}>
            Next: Select Locations &rarr;
          </button>
        </div>
      </div>

      {/* Sidebar: Themes */}
      <div style={{ width: 280, borderLeft: "1px solid #333", padding: 16, background: "#0a0f14" }}>
        <h3 style={{ color: "#fff", marginBottom: 12 }}>Active Themes</h3>
        {analysis.themes.map((t, i) => (
          <div key={i} style={{ marginBottom: 12, padding: 8, background: "#161b22", borderRadius: 4 }}>
            <div style={{ color: "#fff", fontWeight: "bold", marginBottom: 4 }}>{t.theme.name}</div>
            <div style={{ color: "#888", fontSize: 12 }}>
              {Object.entries(t.raw_demands).map(([res, amt]) => (
                <div key={res}>{res}: {amt.toFixed(1)}/min</div>
              ))}
            </div>
          </div>
        ))}

        <h3 style={{ color: "#fff", marginTop: 24, marginBottom: 12 }}>Raw Resources</h3>
        <div style={{ padding: 8, background: "#161b22", borderRadius: 4 }}>
          {Object.entries(analysis.raw_demands).map(([res, amt]) => (
            <div key={res} style={{ color: "#999", fontSize: 12, marginBottom: 2 }}>
              {res}: {amt.toFixed(1)}/min
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
