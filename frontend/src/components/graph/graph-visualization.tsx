"use client"

import React, { useCallback, useEffect, useState, useMemo, memo } from 'react'
import {
   ReactFlow,
   MiniMap,
   Controls,
   Background,
   useNodesState,
   useEdgesState,
   addEdge,
   Node,
   Edge,
   Connection,
   BackgroundVariant,
   Panel,
 } from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { useGraphQuery, useGraphStatistics } from '@/hooks/use-graph-data'
import { useMemories } from '@/hooks/use-memory-persistence'
import { Expand, Eye, Search, Network } from 'lucide-react'
import { forceDirectedLayout, circularLayout, hierarchicalLayout } from '@/utils/graph-layout'
import { Download } from 'lucide-react'

interface GraphNode {
  id: string
  label: string
  type: string
  properties: Record<string, any>
}

interface GraphEdge {
  source: string
  target: string
  type: string
  properties: Record<string, any>
}

interface GraphData {
  nodes: GraphNode[]
  edges: GraphEdge[]
}

interface GraphVisualizationProps {
   data?: GraphData
   onNodeClick?: (node: GraphNode) => void
   className?: string
   searchEntity?: string
 }

type LayoutType = 'force' | 'circular' | 'hierarchical'

 const nodeTypes = {
   // We'll use the default node type for now
 }

 const GraphVisualization = ({
   data,
   onNodeClick,
   className = "",
   searchEntity
 }: GraphVisualizationProps) => {
   const [nodes, setNodes, onNodesChange] = useNodesState<Node>([])
   const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([])
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null)
  const [searchQuery, setSearchQuery] = useState("")
  const [layoutType, setLayoutType] = useState<LayoutType>('force')
  const [nodeTypeFilter, setNodeTypeFilter] = useState<string | null>(null)
  const [edgeTypeFilter, setEdgeTypeFilter] = useState<string | null>(null)
  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set())

  const containerRef = React.useRef<HTMLDivElement>(null)
  const [containerSize, setContainerSize] = useState({ width: 800, height: 600 })
  
   // Query graph data - show all memories when no specific search
   const { data: queryData } = useGraphQuery({
     entity_name: searchEntity || searchQuery.trim() || undefined,
     depth: 2,
   })

  // Graph data loaded (debug logging removed)

   // Get memories for showing all data when no specific search
   const { data: memories } = useMemories()

   // Use queried data or provided data
   const activeData = queryData && queryData.nodes && queryData.edges &&
     (queryData.nodes.length > 0 || queryData.edges.length > 0) ? queryData : data

   // Track container size
   useEffect(() => {
     const resizeObserver = new ResizeObserver((entries) => {
       for (const entry of entries) {
         const { width, height } = entry.contentRect
         setContainerSize({ width, height })
       }
     })

     if (containerRef.current) {
       resizeObserver.observe(containerRef.current)
     }

     return () => resizeObserver.disconnect()
   }, [])

   // Convert backend data to React Flow format with layout
   useEffect(() => {
     if (!activeData || !activeData.nodes || !activeData.edges) return

     const baseNodes: Node[] = activeData.nodes.map((node, index) => ({
       id: node.id,
       type: 'default',
       position: { x: 0, y: 0 },
       data: {
         label: node.label || node.id,
         originalNode: node,
       },
     }))

     // Convert GraphEdge[] to Edge[] for layout functions
     const layoutEdges: Edge[] = activeData.edges.map((edge, index) => ({
       id: `${edge.source}-${edge.target}-${index}`,
       source: edge.source,
       target: edge.target,
     }))

     // Apply layout based on selected type
     let positionedNodes: Node[]
     switch (layoutType) {
       case 'force':
         positionedNodes = forceDirectedLayout(baseNodes, layoutEdges, containerSize)
         break
       case 'circular':
         positionedNodes = circularLayout(baseNodes, containerSize)
         break
       case 'hierarchical':
         positionedNodes = hierarchicalLayout(baseNodes, layoutEdges, containerSize)
         break
       default:
         positionedNodes = baseNodes.map((node) => ({
           ...node,
           position: {
             x: Math.random() * containerSize.width,
             y: Math.random() * containerSize.height,
           },
         }))
     }

     // Filter nodes by type if filter is set
     const filteredNodes = positionedNodes.filter(node => {
       const nodeType = (node.data?.originalNode as GraphNode)?.type || 'default'
       if (nodeTypeFilter && nodeType !== nodeTypeFilter) return false
       return true
     })

     const flowNodes: Node[] = filteredNodes.map((node) => {
       const nodeType = (node.data?.originalNode as GraphNode)?.type || 'default'
       return {
         ...node,
         position: node.position,
         data: {
           ...node.data,
           label: node.data?.label || node.id,
         },
         style: {
           backgroundColor: getNodeColor(nodeType),
           color: '#ffffff',
           border: '2px solid #1a365d',
           borderRadius: '8px',
           padding: '8px',
           fontSize: '12px',
           fontWeight: 'bold',
           opacity: nodeTypeFilter && nodeType !== nodeTypeFilter ? 0.3 : 1,
         },
       }
     })

     // Filter edges by type if filter is set
     const filteredEdges = activeData.edges.filter(edge => {
       if (edgeTypeFilter && edge.type !== edgeTypeFilter) return false
       return true
     })

     const flowEdges: Edge[] = filteredEdges.map((edge, index) => ({
       id: `${edge.source}-${edge.target}-${index}`,
       source: edge.source,
       target: edge.target,
       type: 'smoothstep',
       label: edge.type,
       style: { 
         stroke: getEdgeColor(edge.type), 
         strokeWidth: 2,
         opacity: edgeTypeFilter && edge.type !== edgeTypeFilter ? 0.3 : 1
       },
       labelStyle: { fontSize: '10px', fill: '#475569' },
     }))

     setNodes(flowNodes)
     setEdges(flowEdges)
   }, [activeData, setNodes, setEdges, layoutType, containerSize, nodeTypeFilter, edgeTypeFilter])

   const exportGraph = useCallback(() => {
     const graphData = {
       nodes: activeData?.nodes || [],
       edges: activeData?.edges || [],
     }
     const blob = new Blob([JSON.stringify(graphData, null, 2)], { type: 'application/json' })
     const url = URL.createObjectURL(blob)
     const link = document.createElement('a')
     link.href = url
     link.download = 'graph-export.json'
     link.click()
     URL.revokeObjectURL(url)
   }, [activeData])

  const getNodeColor = (nodeType: string): string => {
    // Monochrome grayscale palette
    const colors: Record<string, string> = {
      'Entity': '#525252',           // gray-600
      'Paper': '#404040',            // gray-700
      'Author': '#737373',           // gray-500
      'Concept': '#262626',          // gray-800
      'Topic': '#171717',            // gray-900
      'User Message': '#a3a3a3',     // gray-400
      'Assistant Message': '#737373', // gray-500
      'Memory': '#525252',           // gray-600
      'Conversation': '#404040',     // gray-700
      'default': '#737373',          // gray-500
    }
    return colors[nodeType] || colors.default
  }

  const getEdgeColor = (edgeType: string): string => {
    // Monochrome grayscale palette
    const colors: Record<string, string> = {
      'MENTIONS': '#737373',
      'RELATES_TO': '#525252',
      'CITES': '#404040',
      'AUTHORED_BY': '#262626',
      'SUPPORTS': '#525252',
      'CONTRADICTS': '#171717',
      'default': '#a3a3a3',
    }
    return colors[edgeType] || colors.default
  }

  const handleExpandNode = useCallback(async (nodeId: string) => {
    if (expandedNodes.has(nodeId)) return
    
    setExpandedNodes(prev => new Set([...prev, nodeId]))
    
    // Fetch neighbors for this node
    try {
      const response = await fetch('/api/graph/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          entity_name: nodeId,
          depth: 1,
        }),
      })
      
      if (response.ok) {
        const data = await response.json()
        // The graph will automatically update via the query hook
      }
    } catch (err) {
      console.error('Failed to expand node:', err)
    }
  }, [expandedNodes])

  const handleFindPath = useCallback(async (sourceId: string, targetId: string) => {
    try {
      const response = await fetch(`/api/graph/paths?source=${sourceId}&target=${targetId}&max_length=5`)
      if (response.ok) {
        const data = await response.json()
        // Highlight path in graph
        // Path found (debug logging removed)
      }
    } catch (err) {
      console.error('Failed to find path:', err)
    }
  }, [])

  // Get unique node and edge types for filters
  const availableNodeTypes = useMemo(() => {
    if (!activeData?.nodes) return []
    const types = new Set(activeData.nodes.map(n => n.type))
    return Array.from(types).sort()
  }, [activeData])

  const availableEdgeTypes = useMemo(() => {
    if (!activeData?.edges) return []
    const types = new Set(activeData.edges.map(e => e.type))
    return Array.from(types).sort()
  }, [activeData])

  const onConnect = useCallback(
    (params: Edge | Connection) => setEdges((eds) => addEdge(params, eds)),
    [setEdges],
  )

  const handleNodeClick = useCallback((_: React.MouseEvent, node: Node) => {
    const originalNode = node.data.originalNode as GraphNode
    setSelectedNode(originalNode)
    
    if (onNodeClick && originalNode) {
      onNodeClick(originalNode)
    }
  }, [onNodeClick])

  const expandNode = useCallback((nodeName: string) => {
    setSearchQuery(nodeName)
  }, [])

  // Show empty state message when no data
  if (!activeData || !activeData.nodes || !activeData.edges || 
      (activeData.nodes.length === 0 && activeData.edges.length === 0)) {
    return (
      <div className={`w-full h-full flex items-center justify-center ${className}`}>
        <Card className="p-8 max-w-md text-center border border-border/50">
          <div className="space-y-6">
            <div className="w-16 h-16 bg-muted rounded-full flex items-center justify-center mx-auto">
              <Network className="h-8 w-8 text-foreground" />
            </div>
            <div className="space-y-2">
              <h3 className="text-lg font-semibold text-foreground">No Knowledge Graph Data</h3>
              <p className="text-sm text-muted-foreground">
                Start a conversation or upload papers to populate the knowledge graph with memories, entities, and topics.
              </p>
            </div>
            <div className="pt-2">
              <Button variant="outline" size="sm" onClick={() => window.location.href = '/'}>
                Go to Chat
              </Button>
            </div>
          </div>
        </Card>
      </div>
    )
  }

   return (
     <div className={`w-full h-full ${className}`} ref={containerRef}>
       <ReactFlow
         nodes={nodes}
         edges={edges}
         onNodesChange={onNodesChange}
         onEdgesChange={onEdgesChange}
         onConnect={onConnect}
         onNodeClick={handleNodeClick}
         nodeTypes={nodeTypes}
         fitView
         fitViewOptions={{ padding: 0.1 }}
         className="bg-gray-50"
       >
         <Controls />
         <MiniMap
           className="bg-white shadow-lg rounded-lg"
           nodeColor={(node) => getNodeColor((node.data?.originalNode as GraphNode)?.type || 'default')}
           maskColor="rgba(255,255,255,0.8)"
         />
         <Background
           variant={BackgroundVariant.Dots}
           gap={20}
           size={1}
          color="#e2e8f0" 
        />
        
        {/* Controls Panel */}
        <Panel position="top-left">
          <Card className="p-3 shadow-lg space-y-2 max-w-xs">
            <div className="flex items-center gap-2">
              <Search size={16} />
              <input
                type="text"
                placeholder="Search entities..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="px-2 py-1 text-sm border rounded flex-1"
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-foreground">Node Type:</label>
              <select
                value={nodeTypeFilter || ''}
                onChange={(e) => setNodeTypeFilter(e.target.value || null)}
                className="w-full px-3 py-2 text-xs border rounded-md bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all"
                aria-label="Filter by node type"
              >
                <option value="">All Types</option>
                {availableNodeTypes.map(type => (
                  <option key={type} value={type}>{type}</option>
                ))}
              </select>
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-foreground">Edge Type:</label>
              <select
                value={edgeTypeFilter || ''}
                onChange={(e) => setEdgeTypeFilter(e.target.value || null)}
                className="w-full px-3 py-2 text-xs border rounded-md bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all"
                aria-label="Filter by edge type"
              >
                <option value="">All Types</option>
                {availableEdgeTypes.map(type => (
                  <option key={type} value={type}>{type}</option>
                ))}
              </select>
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-foreground">Layout:</label>
              <select
                value={layoutType}
                onChange={(e) => setLayoutType(e.target.value as LayoutType)}
                className="w-full px-3 py-2 text-xs border rounded-md bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all"
                aria-label="Select graph layout"
              >
                <option value="force">Force</option>
                <option value="circular">Circular</option>
                <option value="hierarchical">Hierarchical</option>
              </select>
            </div>
            <Button size="sm" variant="outline" onClick={exportGraph} className="w-full">
              <Download size={14} className="mr-1" />
              Export JSON
            </Button>
          </Card>
        </Panel>

        {/* Node Details Panel */}
        {selectedNode && (
          <Panel position="top-right">
            <Card className="p-4 max-w-sm bg-background border border-border/50">
              <div className="space-y-3">
                <div className="flex items-center justify-between gap-2">
                  <Badge variant="outline" className="text-xs">{selectedNode.type}</Badge>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleExpandNode(selectedNode.id)}
                    disabled={expandedNodes.has(selectedNode.id)}
                    className="h-7 text-xs"
                  >
                    <Expand size={12} className="mr-1" />
                    {expandedNodes.has(selectedNode.id) ? 'Expanded' : 'Expand'}
                  </Button>
                </div>
                
                <h3 className="font-semibold text-foreground text-sm">{selectedNode.label || selectedNode.id}</h3>
                
                {Object.keys(selectedNode.properties).length > 0 && (
                  <div className="text-xs space-y-1.5 pt-2 border-t">
                    {Object.entries(selectedNode.properties)
                      .filter(([key]) => !['id', 'label', 'name'].includes(key))
                      .slice(0, 5)
                      .map(([key, value]) => (
                        <div key={key} className="flex gap-2">
                          <span className="text-muted-foreground font-medium min-w-[80px]">{key}:</span>
                          <span className="text-foreground break-words">{String(value).slice(0, 100)}</span>
                        </div>
                      ))}
                  </div>
                )}
                
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => setSelectedNode(null)}
                  className="mt-2 w-full"
                >
                  Close
                </Button>
              </div>
            </Card>
          </Panel>
        )}
      </ReactFlow>
    </div>
  )
}

export default memo(GraphVisualization)