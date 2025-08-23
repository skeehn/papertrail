"use client"

import React from 'react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Brain, Network, Search, Activity } from 'lucide-react'
import { useGraphStatistics } from '@/hooks/use-graph-data'

interface GraphStatistics {
  node_count: number
  relationship_count: number
  node_types: Record<string, number>
  relationship_types: Record<string, number>
  timestamp: string
  source?: string
}

interface MemoryPanelProps {
  className?: string
  onEntitySelect?: (entityName: string) => void
}

const MemoryPanel = ({ className = "", onEntitySelect }: MemoryPanelProps) => {
  const { data: stats, isLoading, error } = useGraphStatistics()

  if (error) {
    return (
      <div className={`space-y-4 ${className}`}>
        <Card className="p-4">
          <div className="flex items-center gap-2 text-red-500">
            <Activity size={16} />
            <span className="text-sm">Error loading memory data</span>
          </div>
        </Card>
      </div>
    )
  }

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Graph Statistics */}
      <Card className="p-4">
        <div className="flex items-center gap-2 mb-3">
          <Brain className="text-blue-500" size={16} />
          <h3 className="font-semibold text-sm">Memory Statistics</h3>
        </div>
        
        {isLoading ? (
          <div className="space-y-2">
            <div className="h-4 bg-gray-200 rounded animate-pulse" />
            <div className="h-4 bg-gray-200 rounded animate-pulse w-3/4" />
          </div>
        ) : stats ? (
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-600">Nodes:</span>
              <span className="font-medium">{stats.node_count}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Relationships:</span>
              <span className="font-medium">{stats.relationship_count}</span>
            </div>
          </div>
        ) : null}
      </Card>

      {/* Node Types */}
      {stats?.node_types && Object.keys(stats.node_types).length > 0 && (
        <Card className="p-4">
          <div className="flex items-center gap-2 mb-3">
            <Network className="text-green-500" size={16} />
            <h3 className="font-semibold text-sm">Entity Types</h3>
          </div>
          
          <div className="space-y-2">
            {Object.entries(stats.node_types).map(([type, count]) => (
              <div key={type} className="flex items-center justify-between">
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-auto p-1 justify-start font-normal"
                  onClick={() => onEntitySelect?.(type)}
                >
                  <Badge variant="outline" className="mr-2 text-xs">
                    {type}
                  </Badge>
                </Button>
                <span className="text-xs text-gray-500">{count as number}</span>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Relationship Types */}
      {stats?.relationship_types && Object.keys(stats.relationship_types).length > 0 && (
        <Card className="p-4">
          <div className="flex items-center gap-2 mb-3">
            <Search className="text-purple-500" size={16} />
            <h3 className="font-semibold text-sm">Connection Types</h3>
          </div>
          
          <div className="space-y-1">
            {Object.entries(stats.relationship_types).map(([type, count]) => (
              <div key={type} className="flex items-center justify-between text-xs">
                <span className="text-gray-600">{type}:</span>
                <span className="font-medium">{count as number}</span>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Last Updated */}
      {stats?.timestamp && (
        <Card className="p-3">
          <div className="text-xs text-gray-500 text-center">
            Last updated: {new Date(stats.timestamp).toLocaleTimeString()}
          </div>
        </Card>
      )}
    </div>
  )
}

export default MemoryPanel