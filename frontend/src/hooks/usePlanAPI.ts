import type {
  TargetItem, Recipe, Theme, AnalyzeResult,
  LocationCandidate, AllocationResult, FactoryResult,
  ResourceNode
} from "../types/plan"

const API = "/api"

async function fetchJSON<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  })
  if (!res.ok) throw new Error(`API error: ${res.status}`)
  return res.json()
}

export function usePlanAPI() {
  return {
    getTargetItems: () =>
      fetchJSON<TargetItem[]>(`${API}/items/targets`),

    getRecipes: (itemName: string) =>
      fetchJSON<Recipe[]>(`${API}/recipes?item_name=${encodeURIComponent(itemName)}`),

    getThemes: () =>
      fetchJSON<Theme[]>(`${API}/themes`),

    analyze: (targetItem: string, targetRate: number, excludedRecipes: string[], maxFactories: number) =>
      fetchJSON<AnalyzeResult>(`${API}/plan/analyze`, {
        method: "POST",
        body: JSON.stringify({
          target_item: targetItem,
          target_rate: targetRate,
          excluded_recipes: excludedRecipes,
          max_factories: maxFactories,
        }),
      }),

    findLocations: (themes: { theme_id: string; critical_resources: Record<string, number> }[],
                     searchRadiusM: number, excludedQuadrants: string[], nResults: number) =>
      fetchJSON<Record<string, LocationCandidate[]>>(`${API}/plan/locations`, {
        method: "POST",
        body: JSON.stringify({
          themes, search_radius_m: searchRadiusM,
          excluded_quadrants: excludedQuadrants, n_results: nResults,
        }),
      }),

    allocate: (factories: { theme_id: string; demands_per_unit: Record<string, number>;
               local_capacity: Record<string, number> }[],
               targetRate: number, trainPenalty: number, waterPenalty: number) =>
      fetchJSON<AllocationResult[]>(`${API}/plan/allocate`, {
        method: "POST",
        body: JSON.stringify({
          factories, target_rate: targetRate,
          train_penalty: trainPenalty, water_penalty: waterPenalty,
        }),
      }),

    generate: (factories: { theme_id: string; target_item: string;
               excluded_recipes: string[]; allocated_rate: number;
               local_resources: Record<string, number> }[]) =>
      fetchJSON<FactoryResult[]>(`${API}/plan/generate`, {
        method: "POST",
        body: JSON.stringify({ factories }),
      }),

    getMapNodes: () =>
      fetchJSON<ResourceNode[]>(`${API}/map/nodes`),
  }
}
