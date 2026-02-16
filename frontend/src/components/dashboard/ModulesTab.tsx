import type { FactoryResult } from "../../types/plan"

interface Props {
  results: FactoryResult[]
}

export default function ModulesTab({ results }: Props) {
  return (
    <div style={{ padding: 16, display: "grid", gap: 16, gridTemplateColumns: "repeat(auto-fill, minmax(350px, 1fr))" }}>
      {results.map(r => (
        <div key={r.theme_id} style={{ background: "#161b22", borderRadius: 8, border: "1px solid #333", padding: 16 }}>
          <h3 style={{ color: "#fff", margin: 0, marginBottom: 12 }}>
            {r.theme_id.replace(/-/g, " ").replace(/\b\w/g, c => c.toUpperCase())}
          </h3>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginBottom: 16 }}>
            <div style={{ background: "#0d1117", padding: 8, borderRadius: 4 }}>
              <div style={{ color: "#fff", fontSize: 20, fontWeight: "bold" }}>{r.module.copies}</div>
              <div style={{ color: "#888", fontSize: 11 }}>Module Copies</div>
            </div>
            <div style={{ background: "#0d1117", padding: 8, borderRadius: 4 }}>
              <div style={{ color: "#fff", fontSize: 20, fontWeight: "bold" }}>{r.module.rate_per_module.toFixed(2)}</div>
              <div style={{ color: "#888", fontSize: 11 }}>Rate/Module</div>
            </div>
            <div style={{ background: "#0d1117", padding: 8, borderRadius: 4 }}>
              <div style={{ color: "#fff", fontSize: 20, fontWeight: "bold" }}>{r.module.buildings_per_module}</div>
              <div style={{ color: "#888", fontSize: 11 }}>Buildings/Module</div>
            </div>
            <div style={{ background: "#0d1117", padding: 8, borderRadius: 4 }}>
              <div style={{ color: "#fbbf24", fontSize: 20, fontWeight: "bold" }}>{r.module.power_per_module.toFixed(1)}</div>
              <div style={{ color: "#888", fontSize: 11 }}>MW/Module</div>
            </div>
          </div>

          <h4 style={{ color: "#ccc", marginBottom: 8 }}>Buildings per Module</h4>
          <table style={{ width: "100%", fontSize: 12, color: "#999", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid #333" }}>
                <th style={{ textAlign: "left", padding: 4 }}>Item</th>
                <th style={{ textAlign: "left", padding: 4 }}>Building</th>
                <th style={{ textAlign: "right", padding: 4 }}>Count</th>
                <th style={{ textAlign: "right", padding: 4 }}>Power</th>
              </tr>
            </thead>
            <tbody>
              {r.module.buildings.map((b, i) => (
                <tr key={i} style={{ borderBottom: "1px solid #222" }}>
                  <td style={{ padding: 4 }}>{b.item}</td>
                  <td style={{ padding: 4 }}>{b.building}</td>
                  <td style={{ textAlign: "right", padding: 4 }}>{b.count}</td>
                  <td style={{ textAlign: "right", padding: 4 }}>{b.power_mw.toFixed(1)} MW</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
    </div>
  )
}
