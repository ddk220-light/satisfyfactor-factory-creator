import { useState, useEffect } from "react"
import type { UserPreferences, AnalyzeResult, LocationCandidate, ResourceNode } from "../../types/plan"
import { usePlanAPI } from "../../hooks/usePlanAPI"
import GameMap from "../map/GameMap"
import ResourceNodes from "../map/ResourceNodes"
import FactoryMarkers from "../map/FactoryMarkers"

interface Props {
  preferences: UserPreferences
  analysis: AnalyzeResult
  onComplete: (selected: Record<string, LocationCandidate>) => void
  onBack: () => void
}

export default function LocationStep({ preferences, analysis, onComplete, onBack }: Props) {
  const api = usePlanAPI()
  const [mapNodes, setMapNodes] = useState<ResourceNode[]>([])
  const [candidates, setCandidates] = useState<Record<string, LocationCandidate[]>>({})
  const [selected, setSelected] = useState<Record<string, LocationCandidate>>({})
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    const themes = analysis.themes.map((t) => ({
      theme_id: t.theme.id,
      critical_resources: t.raw_demands,
    }))

    Promise.all([
      api.getMapNodes(),
      api.findLocations(themes, preferences.searchRadiusM, preferences.excludedQuadrants, 5),
    ])
      .then(([nodes, locs]) => {
        setMapNodes(nodes)
        setCandidates(locs)
        setLoading(false)
      })
      .catch((err) => {
        console.error(err)
        setLoading(false)
      })
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handleSelect = (themeId: string, candidate: LocationCandidate) => {
    setSelected((prev) => ({ ...prev, [themeId]: candidate }))
  }

  const autoSelect = () => {
    const auto: Record<string, LocationCandidate> = {}
    Object.entries(candidates).forEach(([themeId, locs]) => {
      const best = locs[0]
      if (best) auto[themeId] = best
    })
    setSelected(auto)
  }

  const allSelected = analysis.themes.every((t) => selected[t.theme.id])

  if (loading) return <div style={{ padding: 24, color: "#999" }}>Loading map data...</div>

  return (
    <div style={{ display: "flex", height: "calc(100vh - 60px)" }}>
      {/* Map */}
      <div style={{ flex: 1 }}>
        <GameMap>
          <ResourceNodes nodes={mapNodes} />
          <FactoryMarkers candidates={candidates} selected={selected} onSelect={handleSelect} />
        </GameMap>
      </div>

      {/* Sidebar */}
      <div
        style={{
          width: 300,
          borderLeft: "1px solid #333",
          padding: 16,
          background: "#0a0f14",
          overflow: "auto",
        }}
      >
        <h3 style={{ color: "#fff", marginBottom: 12 }}>Select Locations</h3>
        <p style={{ color: "#888", fontSize: 12, marginBottom: 16 }}>
          Click a circle on the map to select one location per theme.
        </p>

        <button
          onClick={autoSelect}
          style={{
            width: "100%",
            padding: "8px",
            background: "#1e3a5f",
            color: "#93c5fd",
            border: "1px solid #2563eb",
            borderRadius: 4,
            cursor: "pointer",
            marginBottom: 16,
          }}
        >
          Auto-select Best
        </button>

        {analysis.themes.map((t) => {
          const sel = selected[t.theme.id]
          return (
            <div
              key={t.theme.id}
              style={{
                marginBottom: 12,
                padding: 8,
                background: "#161b22",
                borderRadius: 4,
                border: sel ? "1px solid #2563eb" : "1px solid #333",
              }}
            >
              <div style={{ color: "#fff", fontWeight: "bold", marginBottom: 4 }}>{t.theme.name}</div>
              {sel ? (
                <div style={{ color: "#93c5fd", fontSize: 12 }}>
                  Score: {sel.score.toFixed(0)}
                </div>
              ) : (
                <div style={{ color: "#f87171", fontSize: 12 }}>Not selected</div>
              )}
            </div>
          )
        })}

        <div style={{ marginTop: 24, display: "flex", gap: 8 }}>
          <button
            onClick={onBack}
            style={{
              flex: 1,
              padding: "8px",
              background: "#333",
              color: "#ccc",
              border: "1px solid #555",
              borderRadius: 4,
              cursor: "pointer",
            }}
          >
            &larr; Back
          </button>
          <button
            onClick={() => onComplete(selected)}
            disabled={!allSelected}
            style={{
              flex: 1,
              padding: "8px",
              background: allSelected ? "#2563eb" : "#333",
              color: "#fff",
              border: "none",
              borderRadius: 4,
              cursor: allSelected ? "pointer" : "default",
            }}
          >
            Generate Plan &rarr;
          </button>
        </div>
      </div>
    </div>
  )
}
