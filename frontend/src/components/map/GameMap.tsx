import { MapContainer, useMap } from "react-leaflet"
import L from "leaflet"
import "leaflet/dist/leaflet.css"
import { useEffect } from "react"

// Game world bounds (centimeters) - approximate
const GAME_MIN_X = -375000
const GAME_MAX_X = 425000
const GAME_MIN_Y = -375000
const GAME_MAX_Y = 375000

// Convert game coords to Leaflet LatLng using CRS.Simple
// In CRS.Simple, lat=y, lng=x
export function gameToLatLng(x: number, y: number): L.LatLngExpression {
  // Normalize to 0-1000 range for Leaflet
  const lat = ((y - GAME_MIN_Y) / (GAME_MAX_Y - GAME_MIN_Y)) * 1000
  const lng = ((x - GAME_MIN_X) / (GAME_MAX_X - GAME_MIN_X)) * 1000
  return [lat, lng]
}

function FitBounds() {
  const map = useMap()
  useEffect(() => {
    map.fitBounds([[0, 0], [1000, 1000]])
  }, [map])
  return null
}

interface Props {
  children?: React.ReactNode
}

export default function GameMap({ children }: Props) {
  return (
    <MapContainer
      crs={L.CRS.Simple}
      bounds={[[0, 0], [1000, 1000]]}
      style={{ width: "100%", height: "100%", background: "#0a0f14" }}
      minZoom={-2}
      maxZoom={4}
      zoomSnap={0.5}
    >
      <FitBounds />
      {children}
    </MapContainer>
  )
}
