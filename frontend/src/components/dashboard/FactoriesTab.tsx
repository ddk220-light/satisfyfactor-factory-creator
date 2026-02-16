import { useState } from "react"
import type { FactoryResult } from "../../types/plan"

interface Props {
  results: FactoryResult[]
}

export default function FactoriesTab({ results }: Props) {
  const [expanded, setExpanded] = useState<string | null>(null)

  return (
    <div style={{ padding: 16, display: "grid", gap: 16, gridTemplateColumns: "repeat(auto-fill, minmax(350px, 1fr))" }}>
      {results.map(r => (
        <div key={r.theme_id} style={{
          background: "#161b22", borderRadius: 8, border: "1px solid #333",
          overflow: "hidden",
        }}>
          {/* Card header */}
          <div style={{ padding: 16, borderBottom: "1px solid #333", cursor: "pointer" }}
            onClick={() => setExpanded(expanded === r.theme_id ? null : r.theme_id)}
          >
            <h3 style={{ color: "#fff", margin: 0, marginBottom: 8 }}>
              {r.theme_id.replace(/-/g, " ").replace(/\b\w/g, c => c.toUpperCase())}
            </h3>
            <div style={{ display: "flex", gap: 16, fontSize: 13, color: "#999" }}>
              <span>{r.plan.total_buildings} buildings</span>
              <span>{r.plan.total_power_mw.toFixed(1)} MW</span>
              <span>{r.plan.target_rate.toFixed(1)}/min</span>
            </div>
          </div>

          {/* Expanded detail */}
          {expanded === r.theme_id && (
            <div style={{ padding: 16 }}>
              {/* Building summary */}
              <h4 style={{ color: "#ccc", marginBottom: 8 }}>Building Summary</h4>
              <div style={{ marginBottom: 12 }}>
                {Object.entries(r.plan.building_summary).map(([bldg, count]) => (
                  <div key={bldg} style={{ display: "flex", justifyContent: "space-between", color: "#999", fontSize: 13, padding: "2px 0" }}>
                    <span>{bldg}</span><span>x{count}</span>
                  </div>
                ))}
              </div>

              {/* Raw demands */}
              <h4 style={{ color: "#ccc", marginBottom: 8 }}>Raw Resources</h4>
              <div style={{ marginBottom: 12 }}>
                {Object.entries(r.plan.raw_demands).map(([res, amt]) => (
                  <div key={res} style={{ display: "flex", justifyContent: "space-between", color: "#999", fontSize: 13, padding: "2px 0" }}>
                    <span>{res}</span><span>{amt.toFixed(1)}/min</span>
                  </div>
                ))}
              </div>

              {/* Train imports */}
              {Object.keys(r.plan.train_imports).length > 0 && (
                <>
                  <h4 style={{ color: "#60a5fa", marginBottom: 8 }}>Train Imports</h4>
                  {Object.entries(r.plan.train_imports).map(([res, amt]) => (
                    <div key={res} style={{ display: "flex", justifyContent: "space-between", color: "#60a5fa", fontSize: 13, padding: "2px 0" }}>
                      <span>{res}</span><span>{amt.toFixed(1)}/min</span>
                    </div>
                  ))}
                </>
              )}

              {/* Per-building detail table */}
              <h4 style={{ color: "#ccc", marginTop: 12, marginBottom: 8 }}>All Buildings</h4>
              <table style={{ width: "100%", fontSize: 12, color: "#999", borderCollapse: "collapse" }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid #333" }}>
                    <th style={{ textAlign: "left", padding: 4 }}>Item</th>
                    <th style={{ textAlign: "left", padding: 4 }}>Building</th>
                    <th style={{ textAlign: "right", padding: 4 }}>Count</th>
                    <th style={{ textAlign: "right", padding: 4 }}>Clock</th>
                    <th style={{ textAlign: "right", padding: 4 }}>Power</th>
                  </tr>
                </thead>
                <tbody>
                  {r.plan.buildings.map((b, i) => (
                    <tr key={i} style={{ borderBottom: "1px solid #222" }}>
                      <td style={{ padding: 4 }}>{b.item}</td>
                      <td style={{ padding: 4 }}>{b.building}</td>
                      <td style={{ textAlign: "right", padding: 4 }}>{b.count}</td>
                      <td style={{ textAlign: "right", padding: 4 }}>{b.last_clock_pct.toFixed(0)}%</td>
                      <td style={{ textAlign: "right", padding: 4 }}>{b.power_mw.toFixed(1)} MW</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
