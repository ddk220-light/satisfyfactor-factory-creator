import { CircleMarker, Tooltip } from "react-leaflet"
import type { LocationCandidate } from "../../types/plan"
import { gameToLatLng } from "./GameMap"

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
  candidates: Record<string, LocationCandidate[]>
  selected: Record<string, LocationCandidate>
  onSelect: (themeId: string, candidate: LocationCandidate) => void
}

export default function FactoryMarkers({ candidates, selected, onSelect }: Props) {
  return (
    <>
      {Object.entries(candidates).map(([themeId, locs]) =>
        locs.map((loc, i) => {
          const isSelected = selected[themeId] === loc
          const color = THEME_COLORS[themeId] || "#888"
          return (
            <CircleMarker
              key={`${themeId}-${i}`}
              center={gameToLatLng(loc.center.x, loc.center.y)}
              radius={isSelected ? 14 : 10}
              pathOptions={{
                fillColor: color,
                fillOpacity: isSelected ? 0.9 : 0.5,
                color: isSelected ? "#fff" : color,
                weight: isSelected ? 3 : 1,
              }}
              eventHandlers={{
                click: () => onSelect(themeId, loc),
              }}
            >
              <Tooltip>
                {themeId} (Score: {loc.score.toFixed(0)})
                {isSelected ? " \u2713" : ""}
              </Tooltip>
            </CircleMarker>
          )
        })
      )}
    </>
  )
}
