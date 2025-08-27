"use client"

import React from 'react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { 
  Brain, 
  Network, 
  Clock, 
  TrendingUp, 
  Layers,
  Zap,
  Archive,
  Activity,
  BarChart3
} from 'lucide-react'
import { 
  useTemporalMemories, 
  useTemporalMemoryStats,
  useAccessTemporalMemory,
  useMemoryLayerStats
} from '@/hooks/use-memory-persistence'

interface TemporalMemoryPanelProps {
  className?: string
}

const TemporalMemoryPanel = ({ className = "" }: TemporalMemoryPanelProps) => {
  const { data: memories, isLoading: memoriesLoading } = useTemporalMemories()
  const { data: stats, isLoading: statsLoading } = useTemporalMemoryStats()
  const { data: layerStats, isLoading: layerStatsLoading } = useMemoryLayerStats()
  const accessMemory = useAccessTemporalMemory()

  const handleMemoryClick = (memoryId: string) => {
    accessMemory.mutate(memoryId)
  }

  if (memoriesLoading || statsLoading || layerStatsLoading) {
    return (
      <div className={`space-y-4 ${className}`}>
        <Card className="p-4">
          <div className="animate-pulse">
            <div className="h-4 bg-gray-200 rounded w-3/4 mb-2" />
            <div className="h-4 bg-gray-200 rounded w-1/2" />
          </div>
        </Card>
      </div>
    )
  }

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Temporal Memory Statistics */}
      <Card className="p-4">
        <div className="flex items-center gap-2 mb-3">
          <Brain className="text-purple-500" size={16} />
          <h3 className="font-semibold text-sm">Temporal Memory System</h3>
        </div>
        
        {stats && (
          <div className="space-y-3">
            {/* Main stats */}
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600">Active:</span>
                <span className="font-medium">{stats.active_memories}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Total:</span>
                <span className="font-medium">{stats.total_memories}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Confidence:</span>
                <span className="font-medium">{(stats.average_confidence * 100).toFixed(0)}%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Importance:</span>
                <span className="font-medium">{(stats.average_importance * 100).toFixed(0)}%</span>
              </div>
            </div>

            {/* Activity indicators */}
            <div className="flex items-center justify-between text-xs text-gray-500">
              <div className="flex items-center gap-1">
                <Activity size={12} />
                <span>Last hour: {stats.memories_last_hour}</span>
              </div>
              <div className="flex items-center gap-1">
                <TrendingUp size={12} />
                <span>Today: {stats.memories_last_day}</span>
              </div>
            </div>
          </div>
        )}
      </Card>

      {/* Memory Layers */}
      {stats?.by_layer && Object.keys(stats.by_layer).length > 0 && (
        <Card className="p-4">
          <div className="flex items-center gap-2 mb-3">
            <Layers className="text-blue-500" size={16} />
            <h3 className="font-semibold text-sm">Memory Layers</h3>
          </div>
          
          <div className="space-y-2">
            {Object.entries(stats.by_layer).map(([layer, count]) => (
              <div key={layer} className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className={`w-2 h-2 rounded-full ${
                    layer === 'hot' ? 'bg-red-400' :
                    layer === 'warm' ? 'bg-yellow-400' : 'bg-blue-400'
                  }`} />
                  <span className="text-sm capitalize">{layer}</span>
                </div>
                <Badge variant="outline" className="text-xs">
                  {String(count)}
                </Badge>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Memory Types */}
      {stats?.by_type && Object.keys(stats.by_type).length > 0 && (
        <Card className="p-4">
          <div className="flex items-center gap-2 mb-3">
            <BarChart3 className="text-green-500" size={16} />
            <h3 className="font-semibold text-sm">Memory Types</h3>
          </div>
          
          <div className="space-y-2">
            {Object.entries(stats.by_type).map(([type, count]) => (
              <div key={type} className="flex items-center justify-between text-sm">
                <span className="capitalize">{type.replace('_', ' ')}</span>
                <Badge variant="outline" className="text-xs">
                  {String(count)}
                </Badge>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Recent Memories */}
      {memories && memories.length > 0 && (
        <Card className="p-4">
          <div className="flex items-center gap-2 mb-3">
            <Clock className="text-orange-500" size={16} />
            <h3 className="font-semibold text-sm">Recent Memories</h3>
          </div>
          
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {memories.slice(0, 5).map((memory) => (
              <div 
                key={memory.id} 
                className="p-2 bg-gray-50 rounded text-xs cursor-pointer hover:bg-gray-100 transition-colors"
                onClick={() => handleMemoryClick(memory.id)}
              >
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2">
                    <Badge variant="secondary" className="text-xs">
                      {memory.memory_type}
                    </Badge>
                    <div className={`w-1.5 h-1.5 rounded-full ${
                      memory.memory_layer === 'hot' ? 'bg-red-400' :
                      memory.memory_layer === 'warm' ? 'bg-yellow-400' : 'bg-blue-400'
                    }`} />
                  </div>
                  <div className="flex items-center gap-1 text-gray-500">
                    <span>{(memory.confidence * 100).toFixed(0)}%</span>
                  </div>
                </div>
                
                <div className="text-gray-700 mb-1">
                  {memory.content.slice(0, 80)}...
                </div>
                
                <div className="flex items-center justify-between text-gray-400">
                  <span>{new Date(memory.t_accessed).toLocaleDateString()}</span>
                  <div className="flex items-center gap-2">
                    {memory.entities.length > 0 && (
                      <div className="flex items-center gap-1">
                        <Network size={10} />
                        <span>{memory.entities.length}</span>
                      </div>
                    )}
                    {memory.access_count > 0 && (
                      <div className="flex items-center gap-1">
                        <Zap size={10} />
                        <span>{memory.access_count}</span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
          
          {memories.length > 5 && (
            <div className="mt-2 text-center text-xs text-gray-500">
              ... and {memories.length - 5} more memories
            </div>
          )}
        </Card>
      )}

      {/* Hierarchical Memory Performance */}
      {layerStats && (
        <Card className="p-4">
          <div className="flex items-center gap-2 mb-3">
            <Zap className="text-yellow-500" size={16} />
            <h3 className="font-semibold text-sm">Memory Performance</h3>
          </div>
          
          <div className="space-y-3">
            <div className="grid grid-cols-3 gap-2 text-xs">
              <div className="text-center p-2 bg-red-50 rounded">
                <div className="font-medium text-red-600">Hot</div>
                <div className="text-gray-600">{layerStats.hot.count}</div>
                <div className="text-gray-500">~{layerStats.hot.average_access_time_ms}ms</div>
              </div>
              <div className="text-center p-2 bg-yellow-50 rounded">
                <div className="font-medium text-yellow-600">Warm</div>
                <div className="text-gray-600">{layerStats.warm.count}</div>
                <div className="text-gray-500">~{layerStats.warm.average_access_time_ms}ms</div>
              </div>
              <div className="text-center p-2 bg-blue-50 rounded">
                <div className="font-medium text-blue-600">Cold</div>
                <div className="text-gray-600">{layerStats.cold.count}</div>
                <div className="text-gray-500">~{layerStats.cold.average_access_time_ms}ms</div>
              </div>
            </div>
            
            <div className="flex justify-between text-xs text-gray-500">
              <span>Cache Hit: {(layerStats.warm.cache_hit_rate * 100).toFixed(0)}%</span>
              <span>Compression: {(layerStats.cold.compression_ratio * 100).toFixed(0)}%</span>
            </div>
          </div>
        </Card>
      )}

      {/* System Health */}
      <Card className="p-3">
        <div className="text-xs text-gray-500 text-center space-y-1">
          <div className="flex items-center justify-center gap-1">
            <Archive size={12} />
            <span>Hierarchical Memory System Active</span>
          </div>
          {stats && (
            <div>
              {stats.relationship_density.toFixed(1)} avg relationships/memory
            </div>
          )}
        </div>
      </Card>
    </div>
  )
}

export default TemporalMemoryPanel