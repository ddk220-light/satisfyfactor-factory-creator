import { useState, useEffect } from "react"
import type { UserPreferences, TargetItem } from "../../types/plan"
import { usePlanAPI } from "../../hooks/usePlanAPI"

interface Props {
  onComplete: (prefs: UserPreferences) => void
}

export default function PreferencesStep({ onComplete }: Props) {
  const api = usePlanAPI()
  const [items, setItems] = useState<TargetItem[]>([])
  const [search, setSearch] = useState("")
  const [targetItem, setTargetItem] = useState("")
  const [targetRate, setTargetRate] = useState(10)
  const [maxFactories, setMaxFactories] = useState(8)
  const [autoFactories, setAutoFactories] = useState(true)
  const [optimization, setOptimization] = useState<"balanced" | "min_buildings" | "min_power">("balanced")
  const [trainPenalty, setTrainPenalty] = useState(2)
  const [searchRadiusM, setSearchRadiusM] = useState(500)
  const [excludedQuadrants, setExcludedQuadrants] = useState<string[]>([])

  useEffect(() => {
    api.getTargetItems().then(setItems).catch(console.error)
  }, [])

  const filteredItems = items.filter(i =>
    i.name.toLowerCase().includes(search.toLowerCase())
  )

  const toggleQuadrant = (q: string) => {
    setExcludedQuadrants(prev =>
      prev.includes(q) ? prev.filter(x => x !== q) : [...prev, q]
    )
  }

  const handleSubmit = () => {
    if (!targetItem) return
    onComplete({
      targetItem,
      targetRate,
      maxFactories: autoFactories ? 8 : maxFactories,
      optimization,
      trainPenalty,
      searchRadiusM,
      excludedQuadrants,
      excludedRecipes: [],
    })
  }

  const labelStyle = { display: "block" as const, marginBottom: 4, color: "#999", fontSize: 12 }
  const inputStyle = { background: "#161b22", border: "1px solid #333", color: "#ccc", padding: "6px 10px", borderRadius: 4, width: "100%" }

  return (
    <div style={{ padding: 24, maxWidth: 600 }}>
      <h2 style={{ color: "#fff", marginBottom: 24 }}>Production Target</h2>

      {/* Target item search */}
      <div style={{ marginBottom: 16 }}>
        <label style={labelStyle}>Target Item</label>
        <input
          style={inputStyle}
          placeholder="Search items..."
          value={targetItem || search}
          onChange={e => { setSearch(e.target.value); setTargetItem("") }}
        />
        {search && !targetItem && (
          <div style={{ background: "#161b22", border: "1px solid #333", maxHeight: 200, overflow: "auto", borderRadius: 4 }}>
            {filteredItems.slice(0, 20).map(item => (
              <div
                key={item.id}
                style={{ padding: "6px 10px", cursor: "pointer", borderBottom: "1px solid #222" }}
                onClick={() => { setTargetItem(item.name); setSearch("") }}
                onMouseEnter={e => (e.currentTarget.style.background = "#1f2937")}
                onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
              >
                {item.name}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Target rate */}
      <div style={{ marginBottom: 16 }}>
        <label style={labelStyle}>Target Rate (items/min): {targetRate}</label>
        <input type="range" min={1} max={200} value={targetRate}
          onChange={e => setTargetRate(Number(e.target.value))}
          style={{ width: "80%" }}
        />
        <input type="number" min={1} value={targetRate}
          onChange={e => setTargetRate(Number(e.target.value))}
          style={{ ...inputStyle, width: 70, marginLeft: 8, display: "inline-block" }}
        />
      </div>

      {/* Factories */}
      <div style={{ marginBottom: 16 }}>
        <label style={labelStyle}>Number of Factories</label>
        <label style={{ color: "#ccc", marginRight: 16 }}>
          <input type="checkbox" checked={autoFactories}
            onChange={e => setAutoFactories(e.target.checked)} /> Auto
        </label>
        {!autoFactories && (
          <input type="range" min={1} max={8} value={maxFactories}
            onChange={e => setMaxFactories(Number(e.target.value))}
            style={{ width: "60%" }}
          />
        )}
        {!autoFactories && <span style={{ color: "#ccc", marginLeft: 8 }}>{maxFactories}</span>}
      </div>

      {/* Optimization */}
      <div style={{ marginBottom: 16 }}>
        <label style={labelStyle}>Optimization</label>
        {(["balanced", "min_buildings", "min_power"] as const).map(opt => (
          <label key={opt} style={{ color: "#ccc", marginRight: 16 }}>
            <input type="radio" name="optimization" value={opt}
              checked={optimization === opt}
              onChange={() => setOptimization(opt)}
            /> {opt.replace("_", " ").replace(/\b\w/g, c => c.toUpperCase())}
          </label>
        ))}
      </div>

      {/* Train penalty */}
      <div style={{ marginBottom: 16 }}>
        <label style={labelStyle}>Train Import Penalty: {trainPenalty}x</label>
        <input type="range" min={2} max={10} value={trainPenalty}
          onChange={e => setTrainPenalty(Number(e.target.value))}
          style={{ width: "100%" }}
        />
      </div>

      {/* Search radius */}
      <div style={{ marginBottom: 16 }}>
        <label style={labelStyle}>Local Resource Radius: {searchRadiusM}m</label>
        <input type="range" min={200} max={1000} step={50} value={searchRadiusM}
          onChange={e => setSearchRadiusM(Number(e.target.value))}
          style={{ width: "100%" }}
        />
      </div>

      {/* Quadrant exclusion */}
      <div style={{ marginBottom: 24 }}>
        <label style={labelStyle}>Exclude Quadrants (click to toggle)</label>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 4, width: 120 }}>
          {["NW", "NE", "SW", "SE"].map(q => (
            <button key={q} onClick={() => toggleQuadrant(q)}
              style={{
                padding: 8, border: "1px solid #333", borderRadius: 4, cursor: "pointer",
                background: excludedQuadrants.includes(q) ? "#7f1d1d" : "#161b22",
                color: excludedQuadrants.includes(q) ? "#fca5a5" : "#ccc",
              }}
            >
              {q}
            </button>
          ))}
        </div>
      </div>

      <button onClick={handleSubmit} disabled={!targetItem}
        style={{
          padding: "10px 24px", background: targetItem ? "#2563eb" : "#333",
          color: "#fff", border: "none", borderRadius: 4, cursor: targetItem ? "pointer" : "default",
          fontSize: 16,
        }}
      >
        Next: Recipe Selection &rarr;
      </button>
    </div>
  )
}
