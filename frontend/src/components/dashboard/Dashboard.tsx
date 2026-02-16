import { useState, useEffect } from "react"
import type { UserPreferences, AnalyzeResult, LocationCandidate, FactoryResult } from "../../types/plan"
import { usePlanAPI } from "../../hooks/usePlanAPI"
import SummaryBanner from "./SummaryBanner"
import FactoriesTab from "./FactoriesTab"
import MapTab from "./MapTab"
import ModulesTab from "./ModulesTab"
import ExportTab from "./ExportTab"

type DashboardTab = "factories" | "map" | "modules" | "export"

interface Props {
  preferences: UserPreferences
  analysis: AnalyzeResult
  selectedLocations: Record<string, LocationCandidate>
}

export default function Dashboard({ preferences, analysis, selectedLocations }: Props) {
  const api = usePlanAPI()
  const [results, setResults] = useState<FactoryResult[] | null>(null)
  const [tab, setTab] = useState<DashboardTab>("factories")
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const run = async () => {
      try {
        // Step 1: Allocate
        const factories = analysis.themes.map(t => ({
          theme_id: t.theme.id,
          demands_per_unit: t.raw_demands,
          local_capacity: Object.fromEntries(
            Object.entries(t.raw_demands).map(([res, _]) => {
              const loc = selectedLocations[t.theme.id]
              const resInfo = loc?.resources?.[res]
              // Estimate local capacity from nearby node count and purity
              const capacity = resInfo ? resInfo.score * 100 : 0
              return [res, capacity]
            })
          ),
        }))

        const allocations = await api.allocate(
          factories, preferences.targetRate, preferences.trainPenalty, 3.0
        )

        // Step 2: Generate
        const genFactories = allocations.map(a => {
          const themeData = analysis.themes.find(t => t.theme.id === a.theme_id)!
          return {
            theme_id: a.theme_id,
            target_item: preferences.targetItem,
            excluded_recipes: preferences.excludedRecipes,
            allocated_rate: a.allocated_rate,
            local_resources: Object.fromEntries(
              Object.entries(themeData.raw_demands).map(([res, _]) => {
                const loc = selectedLocations[a.theme_id]
                const resInfo = loc?.resources?.[res]
                const capacity = resInfo ? resInfo.score * 100 : 0
                return [res, capacity]
              })
            ),
          }
        })

        const genResults = await api.generate(genFactories)
        setResults(genResults)
        setLoading(false)
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Unknown error")
        setLoading(false)
      }
    }
    run()
  }, [])

  if (loading) return <div style={{ padding: 24, color: "#999" }}>Generating factory plans...</div>
  if (error) return <div style={{ padding: 24, color: "#f87171" }}>Error: {error}</div>
  if (!results) return null

  const tabStyle = (t: DashboardTab) => ({
    padding: "8px 16px", cursor: "pointer", border: "none", borderRadius: "4px 4px 0 0",
    background: tab === t ? "#161b22" : "transparent",
    color: tab === t ? "#fff" : "#666",
    fontWeight: tab === t ? "bold" as const : "normal" as const,
    fontSize: 14,
  })

  return (
    <div>
      <SummaryBanner results={results} />

      {/* Tab bar */}
      <div style={{ display: "flex", gap: 4, padding: "0 16px", borderBottom: "1px solid #333" }}>
        <button style={tabStyle("factories")} onClick={() => setTab("factories")}>Factories</button>
        <button style={tabStyle("map")} onClick={() => setTab("map")}>Map</button>
        <button style={tabStyle("modules")} onClick={() => setTab("modules")}>Modules</button>
        <button style={tabStyle("export")} onClick={() => setTab("export")}>Export</button>
      </div>

      {/* Tab content */}
      {tab === "factories" && <FactoriesTab results={results} />}
      {tab === "map" && <MapTab selectedLocations={selectedLocations} />}
      {tab === "modules" && results && <ModulesTab results={results} />}
      {tab === "export" && results && <ExportTab results={results} />}
    </div>
  )
}
