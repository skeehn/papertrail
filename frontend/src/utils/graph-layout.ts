import { Node, Edge } from '@xyflow/react'

interface GraphNode extends Node {
  degree?: number
}

interface LayoutNode extends GraphNode {
  x: number
  y: number
  vx: number
  vy: number
}

export interface ForceDirectedLayoutOptions {
  width: number
  height: number
  iterations?: number
  repulsionStrength?: number
  attractionStrength?: number
  damping?: number
  cooling?: number
}

const DEFAULT_OPTIONS: Required<ForceDirectedLayoutOptions> = {
  width: 800,
  height: 600,
  iterations: 100,
  repulsionStrength: 1000,
  attractionStrength: 0.01,
  damping: 0.9,
  cooling: 0.95,
}

export function forceDirectedLayout(
  nodes: Node[],
  edges: Edge[],
  options: Partial<ForceDirectedLayoutOptions> = {}
): Node[] {
  const opts = { ...DEFAULT_OPTIONS, ...options }
  
  if (nodes.length === 0) return []
  
  // Initialize positions with random or centered layout
  const layoutNodes: LayoutNode[] = nodes.map((node, index) => ({
    ...node,
    x: opts.width / 2 + (Math.random() - 0.5) * 200,
    y: opts.height / 2 + (Math.random() - 0.5) * 200,
    vx: 0,
    vy: 0,
  }))
  
  // Calculate node degrees
  const nodeDegrees = new Map<string, number>()
  nodes.forEach(node => {
    nodeDegrees.set(node.id, 0)
  })
  
  edges.forEach(edge => {
    const sourceDegree = (nodeDegrees.get(edge.source) || 0) + 1
    const targetDegree = (nodeDegrees.get(edge.target) || 0) + 1
    nodeDegrees.set(edge.source, sourceDegree)
    nodeDegrees.set(edge.target, targetDegree)
  })
  
  layoutNodes.forEach(node => {
    node.degree = nodeDegrees.get(node.id) || 0
  })
  
  // Create edge map for quick lookup
  const edgeMap = new Map<string, Set<string>>()
  edges.forEach(edge => {
    if (!edgeMap.has(edge.source)) {
      edgeMap.set(edge.source, new Set())
    }
    if (!edgeMap.has(edge.target)) {
      edgeMap.set(edge.target, new Set())
    }
    edgeMap.get(edge.source)!.add(edge.target)
    edgeMap.get(edge.target)!.add(edge.source)
  })
  
  // Force-directed layout simulation
  for (let iteration = 0; iteration < opts.iterations; iteration++) {
    // Repulsion force (nodes repel each other)
    for (let i = 0; i < layoutNodes.length; i++) {
      const nodeA = layoutNodes[i]
      let fx = 0
      let fy = 0
      
      for (let j = 0; j < layoutNodes.length; j++) {
        if (i === j) continue
        
        const nodeB = layoutNodes[j]
        const dx = nodeA.x - nodeB.x
        const dy = nodeA.y - nodeB.y
        const distance = Math.sqrt(dx * dx + dy * dy)
        
        if (distance === 0) continue
        
        const force = opts.repulsionStrength / (distance * distance)
        fx += (dx / distance) * force
        fy += (dy / distance) * force
      }
      
      nodeA.vx += fx
      nodeA.vy += fy
    }
    
    // Attraction force (connected nodes attract)
    layoutNodes.forEach(node => {
      let fx = 0
      let fy = 0
      
      const neighbors = edgeMap.get(node.id) || new Set()
      neighbors.forEach(neighborId => {
        const neighbor = layoutNodes.find(n => n.id === neighborId)
        if (!neighbor) return
        
        const dx = neighbor.x - node.x
        const dy = neighbor.y - node.y
        const distance = Math.sqrt(dx * dx + dy * dy)
        
        if (distance === 0) return
        
        fx += dx * opts.attractionStrength
        fy += dy * opts.attractionStrength
      })
      
      node.vx += fx
      node.vy += fy
    })
    
    // Center gravity force (pull nodes toward center)
    const centerX = opts.width / 2
    const centerY = opts.height / 2
    
    layoutNodes.forEach(node => {
      node.vx += (centerX - node.x) * 0.01
      node.vy += (centerY - node.y) * 0.01
    })
    
    // Apply velocities and damping
    const maxVelocity = 10
    layoutNodes.forEach(node => {
      node.vx *= opts.damping
      node.vy *= opts.damping
      
      // Limit velocity
      const velocity = Math.sqrt(node.vx * node.vx + node.vy * node.vy)
      if (velocity > maxVelocity) {
        node.vx = (node.vx / velocity) * maxVelocity
        node.vy = (node.vy / velocity) * maxVelocity
      }
      
      node.x += node.vx
      node.y += node.vy
    })
    
    // Keep nodes within bounds
    const padding = 50
    layoutNodes.forEach(node => {
      node.x = Math.max(padding, Math.min(opts.width - padding, node.x))
      node.y = Math.max(padding, Math.min(opts.height - padding, node.y))
    })
  }
  
  // Convert back to React Flow Node format
  return layoutNodes.map(node => ({
    ...node,
    position: { x: node.x, y: node.y },
  }))
}

export function circularLayout(
  nodes: Node[],
  options: Partial<ForceDirectedLayoutOptions> = {}
): Node[] {
  const opts = { ...DEFAULT_OPTIONS, ...options }
  
  if (nodes.length === 0) return []
  
  const centerX = opts.width / 2
  const centerY = opts.height / 2
  const radius = Math.min(opts.width, opts.height) / 2 - 80
  
  return nodes.map((node, index) => ({
    ...node,
    position: {
      x: centerX + radius * Math.cos((2 * Math.PI * index) / nodes.length),
      y: centerY + radius * Math.sin((2 * Math.PI * index) / nodes.length),
    },
  }))
}

export function hierarchicalLayout(
  nodes: Node[],
  edges: Edge[],
  options: Partial<ForceDirectedLayoutOptions> = {}
): Node[] {
  const opts = { ...DEFAULT_OPTIONS, ...options }
  
  if (nodes.length === 0) return []
  
  // Simple hierarchical layout based on node degree
  const nodeLevels = new Map<string, number>()
  const degreeMap = new Map<string, number>()
  
  // Calculate degrees
  edges.forEach(edge => {
    const sourceDegree = (degreeMap.get(edge.source) || 0) + 1
    const targetDegree = (degreeMap.get(edge.target) || 0) + 1
    degreeMap.set(edge.source, sourceDegree)
    degreeMap.set(edge.target, targetDegree)
  })
  
  // Assign levels based on degree (lower degree = higher level)
  const degrees = Array.from(degreeMap.values())
  const minDegree = Math.min(...degrees)
  const maxDegree = Math.max(...degrees)
  const degreeRange = maxDegree - minDegree || 1
  
  nodes.forEach(node => {
    const degree = degreeMap.get(node.id) || 0
    // Normalize degree to 0-1 range, then invert (high degree = low level)
    const normalizedDegree = degreeRange > 0 
      ? (degree - minDegree) / degreeRange
      : 0.5
    const level = Math.floor((1 - normalizedDegree) * 5)
    nodeLevels.set(node.id, level)
  })
  
  const levelHeight = opts.height / 6
  const centerX = opts.width / 2
  
  // Group nodes by level
  const nodesByLevel = new Map<number, Node[]>()
  nodes.forEach(node => {
    const level = nodeLevels.get(node.id) || 0
    if (!nodesByLevel.has(level)) {
      nodesByLevel.set(level, [])
    }
    nodesByLevel.get(level)!.push(node)
  })
  
  // Position nodes by level
  const result: Node[] = []
  nodesByLevel.forEach((levelNodes, level) => {
    const y = level * levelHeight + levelHeight / 2
    const levelWidth = opts.width
    const nodeSpacing = levelWidth / (levelNodes.length + 1)
    
    levelNodes.forEach((node, index) => {
      result.push({
        ...node,
        position: {
          x: nodeSpacing * (index + 1),
          y: y,
        },
      })
    })
  })
  
  return result
}
