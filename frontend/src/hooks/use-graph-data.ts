"use client"

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useMemories } from './use-memory-persistence'

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

interface GraphQueryParams {
  entity_name?: string
  paper_id?: string
  depth?: number
}

export const useGraphStatistics = () => {
  const { data: memories } = useMemories()
  
  return useQuery({
    queryKey: ['graph-statistics', memories?.length],
    queryFn: async () => {
      try {
        const response = await fetch('/api/graph/statistics')
        if (!response.ok) {
          throw new Error('Backend not available')
        }
        return await response.json()
      } catch (error) {
        // Generate statistics based on actual memories
        const memoryCount = memories?.length || 0
        const entities = new Set<string>()
        const topics = new Set<string>()
        const conversationIds = new Set<string>()
        
        memories?.forEach(memory => {
          memory.metadata.entities?.forEach(entity => entities.add(entity))
          memory.metadata.topics?.forEach(topic => topics.add(topic))
          if (memory.metadata.conversation_id) {
            conversationIds.add(memory.metadata.conversation_id)
          }
        })

        return {
          statistics: {
            node_count: memoryCount + entities.size + topics.size,
            relationship_count: memoryCount * 2 + entities.size + topics.size,
            node_types: {
              "Memory": memoryCount,
              "Entity": entities.size,
              "Topic": topics.size,
              "Conversation": conversationIds.size,
            },
            relationship_types: {
              "CONTAINS": entities.size,
              "DISCUSSES": topics.size,
              "PART_OF": conversationIds.size,
              "RELATES_TO": Math.max(1, memoryCount - 1)
            },
          },
          timestamp: new Date().toISOString(),
        }
      }
    },
    refetchInterval: 10000,
    retry: 1,
  })
}

export const useGraphQuery = (params: GraphQueryParams) => {
  const { data: memories } = useMemories()
  
  return useQuery({
    queryKey: ['graph-query', params, memories?.length],
    initialData: { nodes: [], edges: [] }, // Provide default structure
    queryFn: async () => {
      try {
        const response = await fetch('/api/graph/query', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(params),
        })
        
        if (!response.ok) {
          throw new Error('Backend not available')
        }
        
        return await response.json() as GraphData
      } catch (error) {
        // Generate graph from actual memories
        if (!memories || memories.length === 0) {
          return { nodes: [], edges: [] }
        }

        const nodes: GraphNode[] = []
        const edges: GraphEdge[] = []
        const processedEntities = new Set<string>()
        const processedTopics = new Set<string>()

        // Add memory nodes and related entities/topics
        memories.forEach((memory, index) => {
          // Add memory node
          nodes.push({
            id: memory.id,
            label: memory.content.slice(0, 50) + (memory.content.length > 50 ? '...' : ''),
            type: memory.metadata.type === 'user_message' ? 'User Message' : 'Assistant Message',
            properties: {
              content: memory.content,
              timestamp: memory.created_at,
              conversation_id: memory.metadata.conversation_id
            }
          })

          // Add entity nodes and edges
          memory.metadata.entities?.forEach(entity => {
            if (!processedEntities.has(entity)) {
              nodes.push({
                id: `entity_${entity}`,
                label: entity,
                type: 'Entity',
                properties: { name: entity, type: 'extracted_entity' }
              })
              processedEntities.add(entity)
            }

            edges.push({
              source: memory.id,
              target: `entity_${entity}`,
              type: 'CONTAINS',
              properties: { relationship: 'mentions' }
            })
          })

          // Add topic nodes and edges
          memory.metadata.topics?.forEach(topic => {
            if (!processedTopics.has(topic)) {
              nodes.push({
                id: `topic_${topic}`,
                label: topic,
                type: 'Topic',
                properties: { name: topic, type: 'extracted_topic' }
              })
              processedTopics.add(topic)
            }

            edges.push({
              source: memory.id,
              target: `topic_${topic}`,
              type: 'DISCUSSES',
              properties: { relationship: 'about' }
            })
          })

          // Connect sequential messages
          if (index > 0) {
            edges.push({
              source: memories[index - 1].id,
              target: memory.id,
              type: 'FOLLOWED_BY',
              properties: { sequence: index }
            })
          }
        })

        // Filter by search parameter if provided (otherwise show all)
        if (params.entity_name && params.entity_name.trim()) {
          const searchTerm = params.entity_name.toLowerCase()
          const relevantNodeIds = new Set<string>()
          
          // Find nodes matching search term
          nodes.forEach(node => {
            if (node.label.toLowerCase().includes(searchTerm) ||
                node.properties.content?.toLowerCase().includes(searchTerm)) {
              relevantNodeIds.add(node.id)
              
              // Add connected nodes (depth 1)
              edges.forEach(edge => {
                if (edge.source === node.id) relevantNodeIds.add(edge.target)
                if (edge.target === node.id) relevantNodeIds.add(edge.source)
              })
            }
          })
          
          // Filter to relevant subgraph
          const filteredNodes = nodes.filter(node => relevantNodeIds.has(node.id))
          const filteredEdges = edges.filter(edge => 
            relevantNodeIds.has(edge.source) && relevantNodeIds.has(edge.target)
          )
          
          return { nodes: filteredNodes, edges: filteredEdges }
        }

        return { nodes, edges }
      }
    },
    enabled: Boolean(memories && memories.length > 0),
    retry: 1,
  })
}

export const useGraphVisualization = () => {
  return useQuery({
    queryKey: ['graph-visualization'],
    queryFn: async () => {
      const response = await fetch('/api/graph/visualization')
      if (!response.ok) {
        // Return mock visualization data
        return {
          nodes: [],
          edges: [],
          layout: 'force',
          node_size: 'degree',
          edge_weight: 'strength',
        }
      }
      return response.json()
    },
    retry: 1,
  })
}