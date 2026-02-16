import type { FactoryResult } from "../../types/plan"

interface Props {
  results: FactoryResult[]
}

function downloadFile(content: string, filename: string, mimeType: string) {
  const blob = new Blob([content], { type: mimeType })
  const url = URL.createObjectURL(blob)
  const a = document.createElement("a")
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

function generateMarkdown(results: FactoryResult[]): string {
  const totalBuildings = results.reduce((sum, r) => sum + r.plan.total_buildings, 0)
  const totalPower = results.reduce((sum, r) => sum + r.plan.total_power_mw, 0)

  let md = "# Factory Plan\n\n"
  md += `**Factories:** ${results.length} | **Buildings:** ${totalBuildings} | **Power:** ${totalPower.toFixed(1)} MW\n\n`
  md += "---\n\n"

  for (const r of results) {
    const name = r.theme_id.replace(/-/g, " ").replace(/\b\w/g, c => c.toUpperCase())
    md += `## ${name}\n\n`
    md += `- Rate: ${r.plan.target_rate.toFixed(1)}/min\n`
    md += `- Buildings: ${r.plan.total_buildings}\n`
    md += `- Power: ${r.plan.total_power_mw.toFixed(1)} MW\n\n`

    md += "### Building Summary\n\n"
    md += "| Building | Count |\n|----------|-------|\n"
    for (const [bldg, count] of Object.entries(r.plan.building_summary)) {
      md += `| ${bldg} | ${count} |\n`
    }
    md += "\n"

    md += "### Raw Resources\n\n"
    md += "| Resource | Rate |\n|----------|------|\n"
    for (const [res, amt] of Object.entries(r.plan.raw_demands)) {
      md += `| ${res} | ${amt.toFixed(1)}/min |\n`
    }
    md += "\n"

    if (Object.keys(r.plan.train_imports).length > 0) {
      md += "### Train Imports\n\n"
      md += "| Resource | Rate |\n|----------|------|\n"
      for (const [res, amt] of Object.entries(r.plan.train_imports)) {
        md += `| ${res} | ${amt.toFixed(1)}/min |\n`
      }
      md += "\n"
    }

    md += `### Module: ${r.module.copies} copies @ ${r.module.rate_per_module.toFixed(2)}/min each\n\n`
    md += `- Buildings per module: ${r.module.buildings_per_module}\n`
    md += `- Power per module: ${r.module.power_per_module.toFixed(1)} MW\n\n`
    md += "---\n\n"
  }

  return md
}

export default function ExportTab({ results }: Props) {
  const buttonStyle = {
    padding: "12px 24px", background: "#161b22", color: "#ccc",
    border: "1px solid #333", borderRadius: 4, cursor: "pointer",
    fontSize: 14, marginRight: 12,
  }

  return (
    <div style={{ padding: 24 }}>
      <h3 style={{ color: "#fff", marginBottom: 16 }}>Export Plan</h3>
      <p style={{ color: "#888", marginBottom: 24 }}>
        Download the complete factory plan as JSON or a formatted Markdown document.
      </p>
      <button style={buttonStyle}
        onClick={() => downloadFile(JSON.stringify(results, null, 2), "factory-plan.json", "application/json")}>
        Download JSON
      </button>
      <button style={buttonStyle}
        onClick={() => downloadFile(generateMarkdown(results), "factory-plan.md", "text/markdown")}>
        Download Markdown
      </button>
    </div>
  )
}
