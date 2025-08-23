"use client"

import React, { useState } from 'react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { 
  Search, 
  Clock, 
  Zap,
  Layers,
  Activity
} from 'lucide-react'
import { useHierarchicalMemoryRetrieval } from '@/hooks/use-memory-persistence'

interface MemorySearchPanelProps {
  className?: string
}

const MemorySearchPanel = ({ className = "" }: MemorySearchPanelProps) => {
  const [searchQuery, setSearchQuery] = useState("")
  const [searchResults, setSearchResults] = useState<any>(null)
  const memorySearch = useHierarchicalMemoryRetrieval()

  const handleSearch = async () => {
    if (!searchQuery.trim()) return
    
    try {
      const results = await memorySearch.mutateAsync({
        content_query: searchQuery,
        limit: 10
      })
      setSearchResults(results)
    } catch (error) {
      console.error('Memory search failed:', error)
    }
  }

  return (
    <div className={`space-y-4 ${className}`}>
      <Card className="p-4">
        <div className="flex items-center gap-2 mb-3">
          <Search className="text-indigo-500" size={16} />
          <h3 className="font-semibold text-sm">Memory Search</h3>
        </div>
        
        <div className="flex gap-2">
          <Input
            placeholder="Search memories..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
            className="flex-1"
          />
          <Button 
            size="sm" 
            onClick={handleSearch}
            disabled={memorySearch.isPending || !searchQuery.trim()}
          >
            {memorySearch.isPending ? (
              <div className="w-4 h-4 animate-spin border-2 border-gray-300 border-t-blue-500 rounded-full" />
            ) : (
              <Search size={16} />
            )}
          </Button>
        </div>
      </Card>

      {/* Search Results */}
      {searchResults && (
        <Card className="p-4">
          <div className="flex items-center gap-2 mb-3">
            <Activity className="text-green-500" size={16} />
            <h3 className="font-semibold text-sm">Search Results</h3>
            <Badge variant="outline" className="text-xs">
              {searchResults.memories.length} found
            </Badge>
          </div>

          {/* Performance Stats */}
          <div className="mb-4 p-3 bg-gray-50 rounded text-xs">
            <div className="flex items-center justify-between mb-2">
              <span className="font-medium">Search Performance</span>
              <span className="text-gray-600">
                {searchResults.performance.total_time_ms.toFixed(0)}ms
              </span>
            </div>
            
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-1">
                <Layers size={12} />
                <span>Layers: {searchResults.performance.layers_searched.join(" → ")}</span>
              </div>
              <div className="flex items-center gap-1">
                <Zap size={12} />
                <span>Hits: {searchResults.performance.cache_hits}/{searchResults.performance.cache_hits + searchResults.performance.cache_misses}</span>
              </div>
            </div>
          </div>

          {/* Memory Results */}
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {searchResults.memories.map((memory: any) => (
              <div key={memory.id} className="p-3 border rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <Badge variant="secondary" className="text-xs">
                      {memory.memory_type}
                    </Badge>
                    <div className={`w-1.5 h-1.5 rounded-full ${
                      memory.memory_layer === 'hot' ? 'bg-red-400' :
                      memory.memory_layer === 'warm' ? 'bg-yellow-400' : 'bg-blue-400'
                    }`} />
                    <span className="text-xs text-gray-500">{memory.memory_layer}</span>
                  </div>
                  <div className="flex items-center gap-2 text-xs text-gray-500">
                    <span>{(memory.confidence * 100).toFixed(0)}%</span>
                    <Clock size={12} />
                    <span>{new Date(memory.t_accessed).toLocaleDateString()}</span>
                  </div>
                </div>
                
                <div className="text-sm text-gray-700 mb-2">
                  {memory.content.slice(0, 150)}
                  {memory.content.length > 150 && "..."}
                </div>
                
                {memory.entities.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {memory.entities.slice(0, 3).map((entity: string, idx: number) => (
                      <Badge key={idx} variant="outline" className="text-xs">
                        {entity}
                      </Badge>
                    ))}
                    {memory.entities.length > 3 && (
                      <Badge variant="outline" className="text-xs">
                        +{memory.entities.length - 3}
                      </Badge>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
          
          {searchResults.memories.length === 0 && (
            <div className="text-center text-gray-500 text-sm py-4">
              No memories found for "{searchQuery}"
            </div>
          )}
        </Card>
      )}
    </div>
  )
}

export default MemorySearchPanel