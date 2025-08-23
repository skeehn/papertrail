/**
 * Temporal Memory Types - Inspired by Zep and Graphiti patterns
 * Implements bi-temporal knowledge graph with memory evolution tracking
 */

export interface TemporalMemory {
  // Core memory data
  id: string
  content: string
  
  // Bi-temporal tracking (Zep/Graphiti pattern)
  t_created: Date     // When fact was learned (business time)
  t_updated: Date     // When fact was updated (business time)
  t_accessed: Date    // Last access time (system time)
  t_valid_from: Date  // When this version became valid
  t_valid_to?: Date   // When this version became invalid (null = current)
  
  // Memory evolution
  version: number     // Version number for this memory
  parent_id?: string  // Previous version of this memory
  confidence: number  // Decay over time (0.0-1.0)
  importance: number  // Calculated importance score (0.0-1.0)
  access_count: number // How many times accessed
  
  // Context and source
  source_context: string        // Where/how this was learned
  conversation_id: string      // Which conversation this came from
  agent_id?: string           // Which agent created this
  session_id?: string         // Session identifier
  
  // Extracted information
  entities: string[]          // Extracted entities
  topics: string[]           // Extracted topics
  relationships: MemoryRelationship[] // Relationships to other memories
  
  // Memory type and classification
  memory_type: 'episodic' | 'semantic' | 'procedural' | 'working'
  memory_layer: 'hot' | 'warm' | 'cold'  // Storage layer
  
  // Metadata
  tags: string[]
  embedding?: number[]        // Vector embedding for similarity
  metadata: Record<string, any>
}

export interface MemoryRelationship {
  target_memory_id: string
  relationship_type: 'causes' | 'relates_to' | 'contradicts' | 'supports' | 'follows'
  strength: number           // Relationship strength (0.0-1.0)
  created_at: Date
  context?: string          // Why this relationship exists
}

export interface MemoryConsolidation {
  id: string
  source_memories: string[]  // Memories being consolidated
  target_memory: string     // Consolidated result
  consolidation_type: 'merge' | 'summarize' | 'resolve_conflict'
  confidence: number
  created_at: Date
  reasoning: string         // Why consolidation happened
}

export interface MemoryQuery {
  // Temporal queries
  at_time?: Date           // Point-in-time query
  time_range?: {
    from: Date
    to: Date
  }
  
  // Content queries
  content_query?: string
  entity_filter?: string[]
  topic_filter?: string[]
  
  // Quality filters
  min_confidence?: number
  min_importance?: number
  
  // Context filters
  conversation_id?: string
  agent_id?: string
  memory_type?: TemporalMemory['memory_type']
  memory_layer?: TemporalMemory['memory_layer']
  
  // Relationship queries
  related_to?: string      // Find memories related to this memory ID
  relationship_type?: MemoryRelationship['relationship_type']
  
  // Result options
  limit?: number
  offset?: number
  include_historical?: boolean  // Include non-current versions
  order_by?: 'created' | 'accessed' | 'importance' | 'confidence'
  order_direction?: 'asc' | 'desc'
}

export interface MemoryStatistics {
  total_memories: number
  active_memories: number     // Current versions only
  historical_memories: number // All versions
  
  // By type
  by_type: Record<TemporalMemory['memory_type'], number>
  by_layer: Record<TemporalMemory['memory_layer'], number>
  
  // Quality metrics
  average_confidence: number
  average_importance: number
  average_access_count: number
  
  // Temporal metrics
  memories_last_hour: number
  memories_last_day: number
  memories_last_week: number
  
  // Relationship metrics
  total_relationships: number
  relationship_density: number  // Average relationships per memory
  
  // Storage metrics
  memory_size_bytes: number
  embedding_count: number
  
  // Activity metrics
  unique_conversations: number
  unique_agents: number
  active_sessions: number
}

export interface MemoryDecayConfig {
  // Decay parameters
  base_decay_rate: number     // Base decay per day (0.0-1.0)
  access_boost: number        // Confidence boost per access
  importance_protection: number // How much importance protects from decay
  
  // Thresholds
  min_confidence: number      // Below this, memory becomes inactive
  consolidation_threshold: number // When to trigger consolidation
  
  // Temporal windows
  hot_memory_hours: number    // Hours to keep in hot storage
  warm_memory_days: number    // Days to keep in warm storage
  cold_memory_months: number  // Months to keep in cold storage
}