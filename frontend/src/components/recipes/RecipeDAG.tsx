import type { DAGNode } from "../../types/plan"

interface Props {
  dag: DAGNode[]
}

export default function RecipeDAG({ dag }: Props) {
  if (dag.length === 0) return null

  // Build adjacency: item -> node
  const nodeMap = new Map<string, DAGNode>()
  dag.forEach(n => nodeMap.set(n.item, n))

  // Compute depths (BFS from root - first node)
  const depths = new Map<string, number>()
  const root = dag[0]!
  const queue: [string, number][] = [[root.item, 0]]
  while (queue.length > 0) {
    const [item, depth] = queue.shift()!
    if (depths.has(item)) continue
    depths.set(item, depth)
    const node = nodeMap.get(item)
    if (node) {
      node.children.forEach(child => queue.push([child, depth + 1]))
    }
  }

  // Group by depth
  const layers = new Map<number, string[]>()
  depths.forEach((depth, item) => {
    if (!layers.has(depth)) layers.set(depth, [])
    layers.get(depth)!.push(item)
  })

  const maxDepth = Math.max(...layers.keys())
  const maxWidth = Math.max(...Array.from(layers.values()).map(l => l.length))

  const nodeW = 180
  const nodeH = 60
  const layerGap = 100
  const nodeGap = 30
  const svgW = Math.max(600, maxWidth * (nodeW + nodeGap) + 40)
  const svgH = (maxDepth + 1) * (nodeH + layerGap) + 40

  // Position nodes
  const positions = new Map<string, { x: number; y: number }>()
  layers.forEach((items, depth) => {
    const totalW = items.length * nodeW + (items.length - 1) * nodeGap
    const startX = (svgW - totalW) / 2
    items.forEach((item, i) => {
      positions.set(item, {
        x: startX + i * (nodeW + nodeGap),
        y: 20 + depth * (nodeH + layerGap),
      })
    })
  })

  return (
    <svg width={svgW} height={svgH} style={{ display: "block" }}>
      {/* Edges */}
      {dag.map(node =>
        node.children.map(child => {
          const from = positions.get(node.item)
          const to = positions.get(child)
          if (!from || !to) return null
          return (
            <line key={`${node.item}-${child}`}
              x1={from.x + nodeW / 2} y1={from.y + nodeH}
              x2={to.x + nodeW / 2} y2={to.y}
              stroke="#444" strokeWidth={1.5}
            />
          )
        })
      )}
      {/* Nodes */}
      {dag.map(node => {
        const pos = positions.get(node.item)
        if (!pos) return null
        return (
          <g key={node.item} transform={`translate(${pos.x},${pos.y})`}>
            <rect width={nodeW} height={nodeH} rx={6}
              fill="#161b22" stroke="#333" strokeWidth={1} />
            <text x={nodeW / 2} y={18} textAnchor="middle"
              fill="#fff" fontSize={12} fontWeight="bold">
              {node.item}
            </text>
            <text x={nodeW / 2} y={34} textAnchor="middle"
              fill="#888" fontSize={10}>
              {node.building}
            </text>
            <text x={nodeW / 2} y={50} textAnchor="middle"
              fill="#666" fontSize={9}>
              {node.recipe}
            </text>
          </g>
        )
      })}
    </svg>
  )
}
