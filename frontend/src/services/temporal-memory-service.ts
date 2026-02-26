"use client"

import {
  TemporalMemory,
  MemoryQuery,
  MemoryStatistics,
  MemoryRelationship,
  MemoryDecayConfig
} from '@/types/temporal-memory'

/**
 * Temporal Memory Service - Implements Zep/Graphiti patterns
 * Handles bi-temporal memory operations with decay, consolidation, and evolution
 */

const STORAGE_KEY = 'papertrail_temporal_memories'
const CONFIG_KEY = 'papertrail_memory_config'

const DEFAULT_DECAY_CONFIG: MemoryDecayConfig = {
  base_decay_rate: 0.05,      // 5% decay per day
  access_boost: 0.1,          // 10% confidence boost per access
  importance_protection: 0.5,  // Importance reduces decay by up to 50%
  min_confidence: 0.1,        // Below 10%, memory becomes inactive
  consolidation_threshold: 0.8, // Above 80% similarity triggers consolidation
  hot_memory_hours: 24,       // 24 hours in hot storage
  warm_memory_days: 30,       // 30 days in warm storage
  cold_memory_months: 12      // 12 months in cold storage
}

class TemporalMemoryService {
  private config: MemoryDecayConfig = DEFAULT_DECAY_CONFIG
  
  constructor() {
    this.loadConfig()
  }
  
  private loadConfig(): void {
    try {
      if (typeof window !== 'undefined' && window.localStorage) {
        const stored = localStorage.getItem(CONFIG_KEY)
        if (stored) {
          this.config = { ...DEFAULT_DECAY_CONFIG, ...JSON.parse(stored) }
        }
      }
    } catch (error) {
      console.error('Error loading memory config:', error)
    }
  }
  
  private saveConfig(): void {
    try {
      if (typeof window !== 'undefined' && window.localStorage) {
        localStorage.setItem(CONFIG_KEY, JSON.stringify(this.config))
      }
    } catch (error) {
      console.error('Error saving memory config:', error)
    }
  }
  
  private getStoredMemories(): TemporalMemory[] {
    try {
      if (typeof window !== 'undefined' && window.localStorage) {
        const stored = localStorage.getItem(STORAGE_KEY)
        const memories = stored ? JSON.parse(stored) : []
        // Convert date strings back to Date objects
        return memories.map((memory: any) => ({
          ...memory,
          t_created: new Date(memory.t_created),
          t_updated: new Date(memory.t_updated),
          t_accessed: new Date(memory.t_accessed),
          t_valid_from: new Date(memory.t_valid_from),
          t_valid_to: memory.t_valid_to ? new Date(memory.t_valid_to) : undefined,
          relationships: memory.relationships?.map((rel: any) => ({
            ...rel,
            created_at: new Date(rel.created_at)
          })) || []
        }))
      }
      return []
    } catch (error) {
      console.error('Error getting stored memories:', error)
      return []
    }
  }
  
  private saveMemories(memories: TemporalMemory[]): void {
    try {
      if (typeof window !== 'undefined' && window.localStorage) {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(memories))
        console.log('💾 Saved', memories.length, 'temporal memories')
      }
    } catch (error) {
      console.error('Error saving temporal memories:', error)
    }
  }
  
  /**
   * Create a new temporal memory
   */
  async createMemory(
    content: string,
    context: {
      conversation_id: string
      source_context: string
      entities?: string[]
      topics?: string[]
      memory_type?: TemporalMemory['memory_type']
      importance?: number
    }
  ): Promise<TemporalMemory> {
    const now = new Date()
    const memory: TemporalMemory = {
      id: `tmem_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      content,
      
      // Bi-temporal tracking
      t_created: now,
      t_updated: now,
      t_accessed: now,
      t_valid_from: now,
      t_valid_to: undefined, // Current version
      
      // Memory evolution
      version: 1,
      confidence: 1.0,
      importance: context.importance || this.calculateImportance(content, context.entities || []),
      access_count: 0,
      
      // Context
      source_context: context.source_context,
      conversation_id: context.conversation_id,
      
      // Extracted information
      entities: context.entities || this.extractEntities(content),
      topics: context.topics || this.extractTopics(content),
      relationships: [],
      
      // Classification
      memory_type: context.memory_type || this.classifyMemoryType(content),
      memory_layer: this.determineLayer(now),
      
      // Metadata
      tags: [],
      metadata: {}
    }
    
    const memories = this.getStoredMemories()
    
    // Check for similar memories for potential consolidation
    const similarMemories = this.findSimilarMemories(memory, memories)
    
    if (similarMemories.length > 0) {
      // Check if consolidation is needed
      const shouldConsolidate = similarMemories.some(sim => 
        sim.similarity > this.config.consolidation_threshold
      )
      
      if (shouldConsolidate) {
        console.log('🔄 Consolidating similar memory')
        return await this.consolidateMemories([memory, ...similarMemories.map(s => s.memory)])
      }
    }
    
    // Create relationships to existing memories
    memory.relationships = this.findRelationships(memory, memories)
    
    memories.push(memory)
    this.saveMemories(memories)
    
    console.log('✨ Created temporal memory:', memory.id, 'Type:', memory.memory_type)
    return memory
  }
  
  /**
   * Query memories with temporal and content filters
   */
  async queryMemories(query: MemoryQuery): Promise<TemporalMemory[]> {
    let memories = this.getStoredMemories()
    
    // Apply temporal filters
    if (query.at_time) {
      memories = memories.filter(memory => 
        memory.t_valid_from <= query.at_time! && 
        (!memory.t_valid_to || memory.t_valid_to > query.at_time!)
      )
    }
    
    if (query.time_range) {
      memories = memories.filter(memory =>
        memory.t_created >= query.time_range!.from &&
        memory.t_created <= query.time_range!.to
      )
    }
    
    // Apply content filters
    if (query.content_query) {
      const queryLower = query.content_query.toLowerCase()
      memories = memories.filter(memory =>
        memory.content.toLowerCase().includes(queryLower)
      )
    }
    
    if (query.entity_filter) {
      memories = memories.filter(memory =>
        query.entity_filter!.some(entity =>
          memory.entities.includes(entity)
        )
      )
    }
    
    if (query.topic_filter) {
      memories = memories.filter(memory =>
        query.topic_filter!.some(topic =>
          memory.topics.includes(topic)
        )
      )
    }
    
    // Apply quality filters
    if (query.min_confidence !== undefined) {
      memories = memories.filter(memory => memory.confidence >= query.min_confidence!)
    }
    
    if (query.min_importance !== undefined) {
      memories = memories.filter(memory => memory.importance >= query.min_importance!)
    }
    
    // Apply context filters
    if (query.conversation_id) {
      memories = memories.filter(memory => memory.conversation_id === query.conversation_id)
    }
    
    if (query.memory_type) {
      memories = memories.filter(memory => memory.memory_type === query.memory_type)
    }
    
    if (query.memory_layer) {
      memories = memories.filter(memory => memory.memory_layer === query.memory_layer)
    }
    
    // Apply relationship filters
    if (query.related_to) {
      memories = memories.filter(memory =>
        memory.relationships.some(rel => rel.target_memory_id === query.related_to)
      )
    }
    
    // Include only current versions unless specified
    if (!query.include_historical) {
      memories = memories.filter(memory => memory.t_valid_to === undefined)
    }
    
    // Apply sorting
    const orderBy = query.order_by || 'accessed'
    const orderDirection = query.order_direction || 'desc'
    
    memories.sort((a, b) => {
      let aValue: number, bValue: number
      
      switch (orderBy) {
        case 'created':
          aValue = a.t_created.getTime()
          bValue = b.t_created.getTime()
          break
        case 'accessed':
          aValue = a.t_accessed.getTime()
          bValue = b.t_accessed.getTime()
          break
        case 'importance':
          aValue = a.importance
          bValue = b.importance
          break
        case 'confidence':
          aValue = a.confidence
          bValue = b.confidence
          break
        default:
          aValue = a.t_accessed.getTime()
          bValue = b.t_accessed.getTime()
      }
      
      return orderDirection === 'desc' ? bValue - aValue : aValue - bValue
    })
    
    // Apply pagination
    const offset = query.offset || 0
    const limit = query.limit || 50
    
    return memories.slice(offset, offset + limit)
  }
  
  /**
   * Access a memory (updates access time and count)
   */
  async accessMemory(memoryId: string): Promise<TemporalMemory | null> {
    const memories = this.getStoredMemories()
    const memory = memories.find(m => m.id === memoryId)
    
    if (!memory) return null
    
    // Update access information
    memory.t_accessed = new Date()
    memory.access_count += 1
    
    // Apply access boost to confidence
    memory.confidence = Math.min(1.0, memory.confidence + this.config.access_boost)
    
    this.saveMemories(memories)
    
    console.log('👁️ Accessed memory:', memoryId, 'New confidence:', memory.confidence.toFixed(2))
    return memory
  }
  
  /**
   * Run memory decay process
   */
  async runDecayProcess(): Promise<{ processed: number, moved: number, archived: number }> {
    const memories = this.getStoredMemories()
    let processed = 0, moved = 0, archived = 0
    const now = new Date()
    
    for (const memory of memories) {
      if (memory.t_valid_to) continue // Skip historical versions
      
      // Calculate days since last access
      const daysSinceAccess = (now.getTime() - memory.t_accessed.getTime()) / (1000 * 60 * 60 * 24)
      
      // Calculate decay
      const importanceProtection = memory.importance * this.config.importance_protection
      const decayRate = this.config.base_decay_rate * (1 - importanceProtection)
      const decay = decayRate * daysSinceAccess
      
      // Apply decay
      memory.confidence = Math.max(0, memory.confidence - decay)
      
      // Update memory layer based on age and access pattern
      const newLayer = this.determineLayer(memory.t_accessed)
      if (newLayer !== memory.memory_layer) {
        memory.memory_layer = newLayer
        moved++
      }
      
      // Archive memories below threshold
      if (memory.confidence < this.config.min_confidence) {
        memory.t_valid_to = now
        archived++
      }
      
      processed++
    }
    
    this.saveMemories(memories)
    
    console.log('🧠 Memory decay:', { processed, moved, archived })
    return { processed, moved, archived }
  }
  
  /**
   * Get memory statistics
   */
  async getStatistics(): Promise<MemoryStatistics> {
    const memories = this.getStoredMemories()
    const now = new Date()
    const hourAgo = new Date(now.getTime() - 60 * 60 * 1000)
    const dayAgo = new Date(now.getTime() - 24 * 60 * 60 * 1000)
    const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000)
    
    const activeMemories = memories.filter(m => !m.t_valid_to)
    const historicalMemories = memories.filter(m => m.t_valid_to)
    
    // Calculate statistics
    const by_type = activeMemories.reduce((acc, memory) => {
      acc[memory.memory_type] = (acc[memory.memory_type] || 0) + 1
      return acc
    }, {} as Record<TemporalMemory['memory_type'], number>)
    
    const by_layer = activeMemories.reduce((acc, memory) => {
      acc[memory.memory_layer] = (acc[memory.memory_layer] || 0) + 1
      return acc
    }, {} as Record<TemporalMemory['memory_layer'], number>)
    
    const totalRelationships = activeMemories.reduce((sum, memory) => 
      sum + memory.relationships.length, 0
    )
    
    return {
      total_memories: memories.length,
      active_memories: activeMemories.length,
      historical_memories: historicalMemories.length,
      
      by_type,
      by_layer,
      
      average_confidence: activeMemories.reduce((sum, m) => sum + m.confidence, 0) / activeMemories.length || 0,
      average_importance: activeMemories.reduce((sum, m) => sum + m.importance, 0) / activeMemories.length || 0,
      average_access_count: activeMemories.reduce((sum, m) => sum + m.access_count, 0) / activeMemories.length || 0,
      
      memories_last_hour: memories.filter(m => m.t_created > hourAgo).length,
      memories_last_day: memories.filter(m => m.t_created > dayAgo).length,
      memories_last_week: memories.filter(m => m.t_created > weekAgo).length,
      
      total_relationships: totalRelationships,
      relationship_density: totalRelationships / activeMemories.length || 0,
      
      memory_size_bytes: JSON.stringify(memories).length,
      embedding_count: memories.filter(m => m.embedding).length,
      
      unique_conversations: new Set(memories.map(m => m.conversation_id)).size,
      unique_agents: new Set(memories.map(m => m.agent_id).filter(Boolean)).size,
      active_sessions: new Set(memories.map(m => m.session_id).filter(Boolean)).size
    }
  }
  
  // Helper methods
  private calculateImportance(content: string, entities: string[]): number {
    let importance = 0.5 // Base importance
    
    // Length factor (longer content might be more important)
    importance += Math.min(0.2, content.length / 1000)
    
    // Entity factor (more entities might indicate importance)
    importance += Math.min(0.2, entities.length * 0.05)
    
    // Personal information detection
    if (content.toLowerCase().includes('my name') || 
        content.toLowerCase().includes('i am') ||
        content.toLowerCase().includes('i like') ||
        content.toLowerCase().includes('i prefer')) {
      importance += 0.3
    }
    
    return Math.min(1.0, importance)
  }
  
  private extractEntities(content: string): string[] {
    // Simple entity extraction (can be enhanced)
    const entities: string[] = []
    
    // Extract capitalized words
    const capitalizedWords = content.match(/\b[A-Z][a-z]+\b/g) || []
    entities.push(...capitalizedWords.slice(0, 5))
    
    // Extract quoted phrases
    const quotes = content.match(/"([^"]+)"/g) || []
    entities.push(...quotes.slice(0, 3))
    
    return [...new Set(entities)]
  }
  
  private extractTopics(content: string): string[] {
    const topics: string[] = []
    const lowerContent = content.toLowerCase()
    
    // Common topic keywords
    const topicKeywords = [
      'food', 'travel', 'work', 'family', 'hobby', 'preference', 'goal',
      'problem', 'solution', 'idea', 'plan', 'memory', 'experience'
    ]
    
    topicKeywords.forEach(topic => {
      if (lowerContent.includes(topic)) {
        topics.push(topic)
      }
    })
    
    return topics
  }
  
  private classifyMemoryType(content: string): TemporalMemory['memory_type'] {
    const lowerContent = content.toLowerCase()
    
    // Episodic: Personal experiences, events
    if (lowerContent.includes('i did') || lowerContent.includes('yesterday') || 
        lowerContent.includes('last week') || lowerContent.includes('remember when')) {
      return 'episodic'
    }
    
    // Semantic: Facts, knowledge
    if (lowerContent.includes('is defined as') || lowerContent.includes('means') ||
        lowerContent.includes('according to')) {
      return 'semantic'
    }
    
    // Procedural: How to do things
    if (lowerContent.includes('how to') || lowerContent.includes('step by') ||
        lowerContent.includes('procedure')) {
      return 'procedural'
    }
    
    // Default to episodic for personal conversations
    return 'episodic'
  }
  
  private determineLayer(accessTime: Date): TemporalMemory['memory_layer'] {
    const now = new Date()
    const hoursAgo = (now.getTime() - accessTime.getTime()) / (1000 * 60 * 60)
    const daysAgo = hoursAgo / 24
    
    if (hoursAgo <= this.config.hot_memory_hours) {
      return 'hot'
    } else if (daysAgo <= this.config.warm_memory_days) {
      return 'warm'
    } else {
      return 'cold'
    }
  }
  
  private findSimilarMemories(memory: TemporalMemory, existingMemories: TemporalMemory[]): Array<{memory: TemporalMemory, similarity: number}> {
    // Simple similarity based on content and entities
    return existingMemories
      .map(existing => ({
        memory: existing,
        similarity: this.calculateSimilarity(memory, existing)
      }))
      .filter(item => item.similarity > 0.5)
      .sort((a, b) => b.similarity - a.similarity)
  }
  
  private calculateSimilarity(memory1: TemporalMemory, memory2: TemporalMemory): number {
    // Content similarity (simple word overlap)
    const words1 = new Set(memory1.content.toLowerCase().split(/\s+/))
    const words2 = new Set(memory2.content.toLowerCase().split(/\s+/))
    const intersection = new Set([...words1].filter(word => words2.has(word)))
    const union = new Set([...words1, ...words2])
    const contentSimilarity = intersection.size / union.size
    
    // Entity similarity
    const entities1 = new Set(memory1.entities)
    const entities2 = new Set(memory2.entities)
    const entityIntersection = new Set([...entities1].filter(entity => entities2.has(entity)))
    const entityUnion = new Set([...entities1, ...entities2])
    const entitySimilarity = entityUnion.size > 0 ? entityIntersection.size / entityUnion.size : 0
    
    // Weighted combination
    return contentSimilarity * 0.7 + entitySimilarity * 0.3
  }
  
  private findRelationships(memory: TemporalMemory, existingMemories: TemporalMemory[]): MemoryRelationship[] {
    const relationships: MemoryRelationship[] = []
    
    // Find memories in the same conversation
    const conversationMemories = existingMemories.filter(m => 
      m.conversation_id === memory.conversation_id && m.id !== memory.id
    )
    
    conversationMemories.forEach(related => {
      // Temporal relationship (follows)
      if (related.t_created < memory.t_created) {
        relationships.push({
          target_memory_id: related.id,
          relationship_type: 'follows',
          strength: 0.8,
          created_at: new Date(),
          context: 'Same conversation sequence'
        })
      }
      
      // Entity overlap relationship
      const sharedEntities = memory.entities.filter(entity => 
        related.entities.includes(entity)
      )
      
      if (sharedEntities.length > 0) {
        relationships.push({
          target_memory_id: related.id,
          relationship_type: 'relates_to',
          strength: Math.min(1.0, sharedEntities.length * 0.3),
          created_at: new Date(),
          context: `Shared entities: ${sharedEntities.join(', ')}`
        })
      }
    })
    
    return relationships
  }
  
  private async consolidateMemories(memories: TemporalMemory[]): Promise<TemporalMemory> {
    // For now, just return the most recent memory
    // In a full implementation, this would use LLM to merge content
    const mostRecent = memories.sort((a, b) => b.t_created.getTime() - a.t_created.getTime())[0]
    
    // Mark older memories as consolidated
    const allMemories = this.getStoredMemories()
    const now = new Date()
    
    memories.slice(1).forEach(oldMemory => {
      const stored = allMemories.find(m => m.id === oldMemory.id)
      if (stored) {
        stored.t_valid_to = now
        stored.metadata.consolidated_into = mostRecent.id
      }
    })
    
    mostRecent.confidence = Math.min(1.0, mostRecent.confidence + 0.1) // Boost for consolidation
    this.saveMemories(allMemories)
    
    return mostRecent
  }
}

// Export singleton instance
export const temporalMemoryService = new TemporalMemoryService()