export interface TargetItem {
  id: string
  name: string
}

export interface Recipe {
  id: string
  name: string
  duration: number
  building: string
  power_mw: number
  is_alternate: boolean
  inputs: { item: string; quantity: number }[]
  outputs: { item: string; quantity: number }[]
}

export interface Theme {
  id: string
  name: string
  primary_resources: string[]
  description: string
}

export interface DAGNode {
  item: string
  recipe: string
  building: string
  inputs: string[]
  children: string[]
}

export interface AnalyzeResult {
  themes: { theme: Theme; raw_demands: Record<string, number> }[]
  dag: DAGNode[]
  raw_demands: Record<string, number>
}

export interface LocationCandidate {
  center: { x: number; y: number }
  score: number
  resources: Record<string, {
    node_count: number
    purity_breakdown: Record<string, number>
    score: number
  }>
  nearby_nodes: ResourceNode[]
}

export interface ResourceNode {
  type: string
  purity: string
  x: number
  y: number
  z: number
}

export interface AllocationResult {
  theme_id: string
  allocated_rate: number
  effort: number
}

export interface Building {
  item: string
  recipe: string
  building: string
  count_exact: number
  count: number
  last_clock_pct: number
  power_mw: number
}

export interface FactoryPlan {
  target_rate: number
  buildings: Building[]
  total_buildings: number
  total_power_mw: number
  raw_demands: Record<string, number>
  train_imports: Record<string, number>
  local_extraction: Record<string, number>
  building_summary: Record<string, number>
}

export interface Module {
  rate_per_module: number
  copies: number
  buildings_per_module: number
  power_per_module: number
  buildings: Building[]
}

export interface FactoryResult {
  theme_id: string
  plan: FactoryPlan
  module: Module
}

export interface UserPreferences {
  targetItem: string
  targetRate: number
  maxFactories: number
  optimization: "balanced" | "min_buildings" | "min_power"
  trainPenalty: number
  searchRadiusM: number
  excludedQuadrants: string[]
  excludedRecipes: string[]
}
