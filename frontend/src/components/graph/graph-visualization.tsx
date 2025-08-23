"use client"

import React, { useCallback, useEffect, useState } from 'react'
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
  
  // Query graph data - show all memories when no specific search
  const { data: queryData } = useGraphQuery({
    entity_name: searchEntity || searchQuery.trim() || undefined, // undefined means "show all"
    depth: 2,
  })

  // Show debug info when data is available
  if (queryData && (queryData.nodes.length > 0 || queryData.edges.length > 0)) {
    console.log('📊 Graph data loaded:', queryData.nodes.length, 'nodes,', queryData.edges.length, 'edges')
  }
  
  // Get memories for showing all data when no specific search
  const { data: memories } = useMemories()

  // Use queried data or provided data
  const activeData = queryData && queryData.nodes && queryData.edges && 
    (queryData.nodes.length > 0 || queryData.edges.length > 0) ? queryData : data

  // Convert backend data to React Flow format
  useEffect(() => {
    if (!activeData || !activeData.nodes || !activeData.edges) return

    const flowNodes: Node[] = activeData.nodes.map((node, index) => ({
      id: node.id,
      type: 'default',
      position: {
        x: Math.random() * 400, // TODO: Use proper layout algorithm
        y: Math.random() * 400,
      },
      data: {
        label: node.label || node.id,
        originalNode: node,
      },
      style: {
        backgroundColor: getNodeColor(node.type),
        color: '#ffffff',
        border: '2px solid #1a365d',
        borderRadius: '8px',
        padding: '8px',
        fontSize: '12px',
        fontWeight: 'bold',
      },
    }))

    const flowEdges: Edge[] = activeData.edges.map((edge, index) => ({
      id: `${edge.source}-${edge.target}-${index}`,
      source: edge.source,
      target: edge.target,
      type: 'smoothstep',
      label: edge.type,
      style: { stroke: '#64748b', strokeWidth: 2 },
      labelStyle: { fontSize: '10px', fill: '#475569' },
    }))

    setNodes(flowNodes)
    setEdges(flowEdges)
  }, [activeData, setNodes, setEdges])

  const getNodeColor = (nodeType: string): string => {
    const colors = {
      'Entity': '#3b82f6',           // blue
      'Paper': '#10b981',            // green  
      'Author': '#f59e0b',           // yellow
      'Concept': '#8b5cf6',          // purple
      'Topic': '#ef4444',            // red
      'User Message': '#0ea5e9',     // sky blue
      'Assistant Message': '#22c55e', // green
      'Memory': '#6366f1',           // indigo
      'Conversation': '#f97316',     // orange
      'default': '#6b7280',          // gray
    }
    return colors[nodeType as keyof typeof colors] || colors.default
  }

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
        <Card className="p-6 max-w-md text-center">
          <div className="space-y-3">
            <Network className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="font-semibold">No Knowledge Graph Data</h3>
            <p className="text-sm text-gray-600">
              Start a conversation to populate the knowledge graph with memories, entities, and topics.
            </p>
          </div>
        </Card>
      </div>
    )
  }

  return (
    <div className={`w-full h-full ${className}`}>
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
        <Controls className="bg-white shadow-lg rounded-lg" />
        <MiniMap 
          className="bg-white shadow-lg rounded-lg"
          nodeColor={(node) => getNodeColor((node.data?.originalNode as GraphNode)?.type || 'default')}
          maskColor="rgba(255, 255, 255, 0.8)"
        />
        <Background 
          variant={BackgroundVariant.Dots} 
          gap={20} 
          size={1}
          color="#e2e8f0" 
        />
        
        {/* Search Panel */}
        <Panel position="top-left">
          <Card className="p-3 shadow-lg">
            <div className="flex items-center gap-2">
              <Search size={16} />
              <input
                type="text"
                placeholder="Search entities..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="px-2 py-1 text-sm border rounded"
              />
            </div>
          </Card>
        </Panel>

        {/* Node Details Panel */}
        {selectedNode && (
          <Panel position="top-right">
            <Card className="p-4 shadow-lg max-w-sm">
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <Badge variant="outline">{selectedNode.type}</Badge>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => expandNode(selectedNode.label || selectedNode.id)}
                  >
                    <Expand size={12} />
                    Expand
                  </Button>
                </div>
                
                <h3 className="font-semibold">{selectedNode.label || selectedNode.id}</h3>
                
                {Object.keys(selectedNode.properties).length > 0 && (
                  <div className="text-xs space-y-1">
                    {Object.entries(selectedNode.properties)
                      .filter(([key]) => !['id', 'label', 'name'].includes(key))
                      .slice(0, 5)
                      .map(([key, value]) => (
                        <div key={key}>
                          <span className="text-gray-500">{key}:</span>{' '}
                          <span>{String(value).slice(0, 50)}</span>
                        </div>
                      ))}
                  </div>
                )}
                
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => setSelectedNode(null)}
                  className="mt-2"
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

export default GraphVisualization