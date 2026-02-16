import { CircleMarker, Tooltip } from "react-leaflet"
import type { ResourceNode } from "../../types/plan"
import { gameToLatLng } from "./GameMap"

const RESOURCE_COLORS: Record<string, string> = {
  iron: "#b45309",
  copper: "#d97706",
  limestone: "#a3a3a3",
  coal: "#404040",
  caterium: "#eab308",
  quartz: "#f0abfc",
  sulfur: "#facc15",
  bauxite: "#dc2626",
  uranium: "#22c55e",
  oil: "#1e1e1e",
  nitrogen: "#7dd3fc",
  sam: "#c084fc",
  geyser: "#f97316",
  water: "#3b82f6",
}

interface Props {
  nodes: ResourceNode[]
}

export default function ResourceNodes({ nodes }: Props) {
  return (
    <>
      {nodes.map((node, i) => (
        <CircleMarker
          key={i}
          center={gameToLatLng(node.x, node.y)}
          radius={3}
          pathOptions={{
            fillColor: RESOURCE_COLORS[node.type] || "#666",
            fillOpacity: 0.7,
            color: "transparent",
            weight: 0,
          }}
        >
          <Tooltip>
            {node.type} ({node.purity})
          </Tooltip>
        </CircleMarker>
      ))}
    </>
  )
}
