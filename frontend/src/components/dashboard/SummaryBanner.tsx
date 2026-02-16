import type { FactoryResult } from "../../types/plan"

interface Props {
  results: FactoryResult[]
}

export default function SummaryBanner({ results }: Props) {
  const totalBuildings = results.reduce((sum, r) => sum + r.plan.total_buildings, 0)
  const totalPower = results.reduce((sum, r) => sum + r.plan.total_power_mw, 0)
  const totalTrainImports = results.reduce((sum, r) => {
    return sum + Object.values(r.plan.train_imports).reduce((a, b) => a + b, 0)
  }, 0)

  const statStyle = {
    padding: "12px 24px", background: "#161b22", borderRadius: 8,
    textAlign: "center" as const,
  }
  const valueStyle = { fontSize: 28, fontWeight: "bold" as const, color: "#fff" }
  const labelStyle = { fontSize: 11, color: "#888", marginTop: 4 }

  return (
    <div style={{ display: "flex", gap: 16, padding: 16, flexWrap: "wrap" }}>
      <div style={statStyle}>
        <div style={valueStyle}>{results.length}</div>
        <div style={labelStyle}>Factories</div>
      </div>
      <div style={statStyle}>
        <div style={valueStyle}>{totalBuildings}</div>
        <div style={labelStyle}>Total Buildings</div>
      </div>
      <div style={statStyle}>
        <div style={{ ...valueStyle, color: "#fbbf24" }}>{totalPower.toFixed(1)} MW</div>
        <div style={labelStyle}>Total Power</div>
      </div>
      <div style={statStyle}>
        <div style={{ ...valueStyle, color: "#60a5fa" }}>{totalTrainImports.toFixed(1)}/min</div>
        <div style={labelStyle}>Train Imports</div>
      </div>
    </div>
  )
}
