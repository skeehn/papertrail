"use client"

import React, { useEffect, useState, useCallback } from 'react'
import {
  ReactFlow,
  Node,
  Edge,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  Position,
  BackgroundVariant,
  Panel
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { 
  Network,
  FileText,
  Brain,
  AlertTriangle,
  CheckCircle,
  Info
} from 'lucide-react'

interface ArgumentGraphProps {
  papers: any[]
  selectedPaper: any
}

const ArgumentGraph = ({ papers, selectedPaper }: ArgumentGraphProps) => {
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([])
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([])
  const [selectedNode, setSelectedNode] = useState<any>(null)

  // Build graph from paper data
  useEffect(() => {
    if (!selectedPaper) return

    const newNodes: Node[] = []
    const newEdges: Edge[] = []

    // Add paper node (center)
    newNodes.push({
      id: `paper_${selectedPaper.id}`,
      type: 'default',
      position: { x: 400, y: 200 },
      data: {
        label: selectedPaper.title.slice(0, 40) + '...',
        type: 'paper',
        fullData: selectedPaper
      },
      style: {
        backgroundColor: '#3b82f6',
        color: 'white',
        border: '2px solid #1e40af',
        borderRadius: '8px',
        padding: '12px',
        fontSize: '12px',
        fontWeight: 'bold',
        width: 200
      }
    })

    // Add claim nodes
    selectedPaper.claims?.forEach((claim: any, index: number) => {
      const angle = (index * 2 * Math.PI) / selectedPaper.claims.length
      const radius = 200
      const x = 400 + radius * Math.cos(angle)
      const y = 200 + radius * Math.sin(angle)

      newNodes.push({
        id: `claim_${claim.id}`,
        type: 'default',
        position: { x, y },
        data: {
          label: claim.text.slice(0, 50) + '...',
          type: 'claim',
          fullData: claim
        },
        style: {
          backgroundColor: claim.modality === 'strong' ? '#10b981' : '#f59e0b',
          color: 'white',
          border: `2px solid ${claim.modality === 'strong' ? '#059669' : '#d97706'}`,
          borderRadius: '8px',
          padding: '8px',
          fontSize: '10px',
          width: 150
        }
      })

      // Connect claim to paper
      newEdges.push({
        id: `edge_paper_claim_${claim.id}`,
        source: `paper_${selectedPaper.id}`,
        target: `claim_${claim.id}`,
        type: 'smoothstep',
        style: { stroke: '#64748b', strokeWidth: 2 }
      })
    })

    // Add entity nodes (outer ring)
    selectedPaper.entities?.slice(0, 8).forEach((entity: any, index: number) => {
      const angle = (index * 2 * Math.PI) / Math.min(selectedPaper.entities.length, 8)
      const radius = 350
      const x = 400 + radius * Math.cos(angle)
      const y = 200 + radius * Math.sin(angle)

      newNodes.push({
        id: `entity_${entity.id}`,
        type: 'default',
        position: { x, y },
        data: {
          label: entity.text,
          type: 'entity',
          fullData: entity
        },
        style: {
          backgroundColor: '#8b5cf6',
          color: 'white',
          border: '2px solid #7c3aed',
          borderRadius: '12px',
          padding: '6px 12px',
          fontSize: '9px',
          width: 'auto'
        }
      })

      // Connect entities to relevant claims
      selectedPaper.claims?.forEach((claim: any) => {
        if (claim.subject === entity.text || claim.object === entity.text) {
          newEdges.push({
            id: `edge_claim_entity_${claim.id}_${entity.id}`,
            source: `claim_${claim.id}`,
            target: `entity_${entity.id}`,
            type: 'smoothstep',
            style: { 
              stroke: '#a855f7', 
              strokeWidth: 1,
              strokeDasharray: '5,5'
            },
            animated: false
          })
        }
      })
    })

    setNodes(newNodes)
    setEdges(newEdges)
  }, [selectedPaper, setNodes, setEdges])

  const handleNodeClick = useCallback((_: React.MouseEvent, node: Node) => {
    setSelectedNode(node.data)
  }, [])

  const getNodeIcon = (type: string) => {
    switch (type) {
      case 'paper': return <FileText className="w-4 h-4" />
      case 'claim': return <Brain className="w-4 h-4" />
      case 'entity': return <Network className="w-4 h-4" />
      default: return <Info className="w-4 h-4" />
    }
  }

  const getNodeTypeColor = (type: string) => {
    switch (type) {
      case 'paper': return 'bg-blue-100 text-blue-800'
      case 'claim': return 'bg-green-100 text-green-800'
      case 'entity': return 'bg-purple-100 text-purple-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  if (!selectedPaper) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <Network className="w-12 h-12 mx-auto text-gray-300 mb-4" />
          <h3 className="font-medium text-gray-900 mb-2">No Argument Graph</h3>
          <p className="text-sm text-gray-600">
            Select a paper to view its argument structure
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="h-full relative">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={handleNodeClick}
        fitView
        fitViewOptions={{ padding: 0.1 }}
      >
        <Controls className="bg-white shadow-lg" />
        <Background variant={BackgroundVariant.Dots} gap={20} size={1} />
        
        {/* Legend Panel */}
        <Panel position="top-left">
          <Card className="p-3 shadow-lg">
            <h3 className="font-medium text-sm mb-2">Legend</h3>
            <div className="space-y-2 text-xs">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 bg-blue-500 rounded"></div>
                <span>Paper</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 bg-green-500 rounded"></div>
                <span>Strong Claim</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 bg-orange-500 rounded"></div>
                <span>Weak Claim</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 bg-purple-500 rounded"></div>
                <span>Entity</span>
              </div>
            </div>
          </Card>
        </Panel>

        {/* Stats Panel */}
        <Panel position="top-right">
          <Card className="p-3 shadow-lg">
            <h3 className="font-medium text-sm mb-2">Graph Statistics</h3>
            <div className="space-y-1 text-xs">
              <div>Claims: {selectedPaper.claims?.length || 0}</div>
              <div>Entities: {selectedPaper.entities?.length || 0}</div>
              <div>Strong Claims: {selectedPaper.claims?.filter((c: any) => c.modality === 'strong').length || 0}</div>
              <div>Weak Claims: {selectedPaper.claims?.filter((c: any) => c.modality === 'weak').length || 0}</div>
            </div>
          </Card>
        </Panel>

        {/* Node Details Panel */}
        {selectedNode && (
          <Panel position="bottom-right">
            <Card className="p-4 shadow-lg max-w-sm">
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  {getNodeIcon(selectedNode.type)}
                  <Badge className={getNodeTypeColor(selectedNode.type)}>
                    {selectedNode.type}
                  </Badge>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setSelectedNode(null)}
                    className="ml-auto"
                  >
                    ×
                  </Button>
                </div>
                
                <div>
                  <h4 className="font-medium text-sm mb-2">
                    {selectedNode.type === 'paper' ? 'Paper Title' : 
                     selectedNode.type === 'claim' ? 'Claim' : 'Entity'}
                  </h4>
                  <p className="text-xs text-gray-600">
                    {selectedNode.type === 'claim' ? selectedNode.fullData.text :
                     selectedNode.type === 'entity' ? selectedNode.fullData.text :
                     selectedNode.fullData.title}
                  </p>
                </div>

                {selectedNode.type === 'claim' && (
                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      {selectedNode.fullData.modality === 'strong' ? 
                        <CheckCircle className="w-4 h-4 text-green-500" /> :
                        <AlertTriangle className="w-4 h-4 text-orange-500" />
                      }
                      <span className="text-xs">
                        {selectedNode.fullData.modality} claim
                      </span>
                    </div>
                    
                    <div className="text-xs">
                      <span className="text-gray-500">Confidence: </span>
                      <span>{Math.round(selectedNode.fullData.confidence * 100)}%</span>
                    </div>
                    
                    <div className="text-xs">
                      <span className="text-gray-500">Section: </span>
                      <span>{selectedNode.fullData.section}</span>
                    </div>
                  </div>
                )}

                {selectedNode.type === 'entity' && (
                  <div className="space-y-2">
                    <div className="text-xs">
                      <span className="text-gray-500">Type: </span>
                      <span>{selectedNode.fullData.type}</span>
                    </div>
                    <div className="text-xs">
                      <span className="text-gray-500">Mentions: </span>
                      <span>{selectedNode.fullData.mentions}</span>
                    </div>
                  </div>
                )}
              </div>
            </Card>
          </Panel>
        )}
      </ReactFlow>
    </div>
  )
}

export default ArgumentGraph