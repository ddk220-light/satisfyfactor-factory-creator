import { useEffect, useState } from "react"
import type { LocationCandidate, ResourceNode } from "../../types/plan"
import { usePlanAPI } from "../../hooks/usePlanAPI"
import GameMap from "../map/GameMap"
import ResourceNodes from "../map/ResourceNodes"
import { CircleMarker, Tooltip } from "react-leaflet"
import { gameToLatLng } from "../map/GameMap"

const THEME_COLORS: Record<string, string> = {
  "iron-works": "#b45309",
  "oil-refinery": "#1e1e1e",
  "coal-forge": "#404040",
  "copper-electronics": "#d97706",
  "bauxite-refinery": "#dc2626",
  "sulfur-works": "#facc15",
  "quartz-processing": "#f0abfc",
  "uranium-complex": "#22c55e",
}

interface Props {
  selectedLocations: Record<string, LocationCandidate>
}

export default function MapTab({ selectedLocations }: Props) {
  const api = usePlanAPI()
  const [mapNodes, setMapNodes] = useState<ResourceNode[]>([])

  useEffect(() => {
    api.getMapNodes().then(setMapNodes).catch(console.error)
  }, [])

  return (
    <div style={{ height: "calc(100vh - 200px)" }}>
      <GameMap>
        <ResourceNodes nodes={mapNodes} />
        {Object.entries(selectedLocations).map(([themeId, loc]) => (
          <CircleMarker key={themeId}
            center={gameToLatLng(loc.center.x, loc.center.y)}
            radius={14}
            pathOptions={{
              fillColor: THEME_COLORS[themeId] || "#888",
              fillOpacity: 0.9,
              color: "#fff",
              weight: 2,
            }}
          >
            <Tooltip permanent>
              {themeId.replace(/-/g, " ").replace(/\b\w/g, c => c.toUpperCase())}
            </Tooltip>
          </CircleMarker>
        ))}
      </GameMap>
    </div>
  )
}
