"use client"

import { TemporalMemory, MemoryQuery } from '@/types/temporal-memory'

/**
 * Hierarchical Memory Service - Implements SuperMemory/GraphRAG patterns
 * Manages Hot/Warm/Cold memory layers with intelligent data movement
 */

interface HierarchicalMemoryConfig {
  // Layer thresholds (in milliseconds)
  hot_threshold: number      // 24 hours
  warm_threshold: number     // 30 days
  cold_threshold: number     // 1 year
  
  // Access patterns
  hot_access_boost: number   // Boost for accessing hot memories
  promotion_threshold: number // Access count to promote memory
  demotion_threshold: number  // Age threshold for demotion
  
  // Storage limits
  max_hot_memories: number
  max_warm_memories: number
  // Cold memories are unlimited
}

interface MemoryLayerStats {
  hot: {
    count: number
    average_access_time_ms: number
    recent_accesses: number
  }
  warm: {
    count: number
    average_access_time_ms: number
    cache_hit_rate: number
  }
  cold: {
    count: number
    average_access_time_ms: number
    compression_ratio: number
  }
}

const DEFAULT_CONFIG: HierarchicalMemoryConfig = {
  hot_threshold: 24 * 60 * 60 * 1000,      // 24 hours
  warm_threshold: 30 * 24 * 60 * 60 * 1000, // 30 days
  cold_threshold: 365 * 24 * 60 * 60 * 1000, // 1 year
  hot_access_boost: 0.2,
  promotion_threshold: 3,
  demotion_threshold: 7 * 24 * 60 * 60 * 1000, // 7 days
  max_hot_memories: 100,
  max_warm_memories: 1000
}

// Global timer to prevent multiple background optimizations
let optimizationTimer: NodeJS.Timeout | null = null

export class HierarchicalMemoryService {
  private config: HierarchicalMemoryConfig = DEFAULT_CONFIG
  private accessCache: Map<string, number> = new Map() // Memory ID -> last access time
  
  constructor() {
    // COMPLETELY DISABLE background optimization to prevent issues
    if (optimizationTimer) {
      clearInterval(optimizationTimer)
      optimizationTimer = null
    }
    console.log('🚫 Hierarchical memory service initialized with NO background tasks')
  }
  
  /**
   * Hot Memory Layer (Redis/localStorage equivalent)
   * - Current conversation context
   * - Last 24 hours of interactions  
   * - Sub-100ms access time
   */
  async getHotMemories(query?: Partial<MemoryQuery>): Promise<TemporalMemory[]> {
    const startTime = performance.now()
    
    try {
      const hotMemories = this.getStoredMemoriesByLayer('hot')
      const filtered = this.applyQueryFilters(hotMemories, query || {})
      
      // Log access time for monitoring
      const accessTime = performance.now() - startTime
      console.log(`🔥 Hot memory access: ${accessTime.toFixed(1)}ms`)
      
      return filtered
    } catch (error) {
      console.error('Hot memory access failed:', error)
      return []
    }
  }
  
  /**
   * Warm Memory Layer (PostgreSQL equivalent)
   * - Recent conversations (7-30 days)
   * - Frequently accessed facts
   * - Sub-400ms access time
   */
  async getWarmMemories(query?: Partial<MemoryQuery>): Promise<TemporalMemory[]> {
    const startTime = performance.now()
    
    try {
      const warmMemories = this.getStoredMemoriesByLayer('warm')
      const filtered = this.applyQueryFilters(warmMemories, query || {})
      
      // Simulate warm storage access delay (100-400ms)
      await this.simulateWarmAccess()
      
      const accessTime = performance.now() - startTime
      console.log(`🌡️ Warm memory access: ${accessTime.toFixed(1)}ms`)
      
      return filtered
    } catch (error) {
      console.error('Warm memory access failed:', error)
      return []
    }
  }
  
  /**
   * Cold Memory Layer (Neo4j/FAISS equivalent)  
   * - Historical knowledge
   * - Rarely accessed memories
   * - Complex relationship queries
   */
  async getColdMemories(query?: Partial<MemoryQuery>): Promise<TemporalMemory[]> {
    const startTime = performance.now()
    
    try {
      const coldMemories = this.getStoredMemoriesByLayer('cold')
      const filtered = this.applyQueryFilters(coldMemories, query || {})
      
      // Simulate cold storage access delay (500-2000ms)
      await this.simulateColdAccess()
      
      const accessTime = performance.now() - startTime
      console.log(`🧊 Cold memory access: ${accessTime.toFixed(1)}ms`)
      
      return filtered
    } catch (error) {
      console.error('Cold memory access failed:', error)
      return []
    }
  }
  
  /**
   * Intelligent Memory Retrieval
   * Searches across all layers with performance optimization
   */
  async retrieveMemories(query: MemoryQuery): Promise<{
    memories: TemporalMemory[]
    performance: {
      total_time_ms: number
      layers_searched: string[]
      cache_hits: number
      cache_misses: number
    }
  }> {
    const startTime = performance.now()
    const layersSearched: string[] = []
    let cacheHits = 0
    let cacheMisses = 0
    
    try {
      const results: TemporalMemory[] = []
      const limit = query.limit || 20
      
      // 1. Try hot memory first (fastest)
      if (results.length < limit) {
        const hotResults = await this.getHotMemories(query)
        results.push(...hotResults.slice(0, limit - results.length))
        layersSearched.push('hot')
        
        if (hotResults.length > 0) cacheHits++
        else cacheMisses++
      }
      
      // 2. Try warm memory if needed
      if (results.length < limit) {
        const warmResults = await this.getWarmMemories(query)
        results.push(...warmResults.slice(0, limit - results.length))
        layersSearched.push('warm')
        
        if (warmResults.length > 0) cacheHits++
        else cacheMisses++
      }
      
      // 3. Try cold memory for comprehensive search
      if (results.length < limit) {
        const coldResults = await this.getColdMemories(query)
        results.push(...coldResults.slice(0, limit - results.length))
        layersSearched.push('cold')
        
        if (coldResults.length > 0) cacheHits++
        else cacheMisses++
      }
      
      // 4. Promote frequently accessed memories
      await this.checkForPromotions(results)
      
      const totalTime = performance.now() - startTime
      
      console.log(`🎯 Hierarchical retrieval: ${totalTime.toFixed(1)}ms, ${results.length} memories, layers: ${layersSearched.join(' → ')}`)
      
      return {
        memories: results,
        performance: {
          total_time_ms: totalTime,
          layers_searched: layersSearched,
          cache_hits: cacheHits,
          cache_misses: cacheMisses
        }
      }
    } catch (error) {
      console.error('Hierarchical retrieval failed:', error)
      return {
        memories: [],
        performance: {
          total_time_ms: performance.now() - startTime,
          layers_searched: layersSearched,
          cache_hits: cacheHits,
          cache_misses: cacheMisses
        }
      }
    }
  }
  
  /**
   * Memory Layer Statistics
   */
  async getLayerStatistics(): Promise<MemoryLayerStats> {
    const hotMemories = this.getStoredMemoriesByLayer('hot')
    const warmMemories = this.getStoredMemoriesByLayer('warm')
    const coldMemories = this.getStoredMemoriesByLayer('cold')
    
    return {
      hot: {
        count: hotMemories.length,
        average_access_time_ms: 50, // Simulated
        recent_accesses: this.getRecentAccesses('hot')
      },
      warm: {
        count: warmMemories.length,
        average_access_time_ms: 200, // Simulated
        cache_hit_rate: this.calculateCacheHitRate('warm')
      },
      cold: {
        count: coldMemories.length,
        average_access_time_ms: 800, // Simulated
        compression_ratio: this.calculateCompressionRatio()
      }
    }
  }
  
  /**
   * Background Memory Optimization
   * Runs periodically to move memories between layers
   */
  private startBackgroundOptimization(): void {
    // DISABLED: Background optimization causing infinite loops and stability issues
    // Clear any existing timer
    if (optimizationTimer) {
      clearInterval(optimizationTimer)
      optimizationTimer = null
    }
    
    console.log('🚫 Background optimization disabled to prevent stability issues')
    
    // Removed all background timers - optimization is now manual only
    // TODO: Re-implement with proper singleton pattern and stability checks
  }
  
  private async optimizeMemoryLayers(): Promise<void> {
    // COMPLETELY DISABLED - no longer runs any optimization
    console.log('🚫 Memory optimization disabled - skipping')
    return
    
    try {
      const now = Date.now()
      let moved = 0
      
      // Get all memories
      const allMemories = this.getAllStoredMemories()
      
      for (const memory of allMemories) {
        const lastAccess = new Date(memory.t_accessed).getTime()
        const age = now - lastAccess
        const currentLayer = memory.memory_layer
        let newLayer: 'hot' | 'warm' | 'cold' = currentLayer
        
        // Determine optimal layer based on access patterns
        if (memory.access_count >= this.config.promotion_threshold && age < this.config.hot_threshold) {
          newLayer = 'hot'
        } else if (age < this.config.warm_threshold || memory.access_count >= 2) {
          newLayer = 'warm'
        } else {
          newLayer = 'cold'
        }
        
        // Move memory if layer changed
        if (newLayer !== currentLayer) {
          memory.memory_layer = newLayer
          moved++
          console.log(`📦 Moved memory ${memory.id} from ${currentLayer} → ${newLayer}`)
        }
      }
      
      // Enforce layer limits
      await this.enforceLayerLimits(allMemories)
      
      // Save changes
      this.saveAllMemories(allMemories)
      
      console.log(`✅ Optimization complete: ${moved} memories moved`)
    } catch (error) {
      console.error('Memory optimization failed:', error)
    }
  }

  private async enforceLayerLimits(memories: TemporalMemory[]): Promise<void> {
    // Hot layer limit
    const hotMemories = memories.filter(m => m.memory_layer === 'hot')
    if (hotMemories.length > this.config.max_hot_memories) {
      // Move least recently accessed hot memories to warm
      hotMemories
        .sort((a, b) => new Date(a.t_accessed).getTime() - new Date(b.t_accessed).getTime())
        .slice(0, hotMemories.length - this.config.max_hot_memories)
        .forEach(memory => {
          memory.memory_layer = 'warm'
          console.log(`📦 Hot overflow: moved ${memory.id} to warm`)
        })
    }
    
    // Warm layer limit  
    const warmMemories = memories.filter(m => m.memory_layer === 'warm')
    if (warmMemories.length > this.config.max_warm_memories) {
      // Move least recently accessed warm memories to cold
      warmMemories
        .sort((a, b) => new Date(a.t_accessed).getTime() - new Date(b.t_accessed).getTime())
        .slice(0, warmMemories.length - this.config.max_warm_memories)
        .forEach(memory => {
          memory.memory_layer = 'cold'
          console.log(`📦 Warm overflow: moved ${memory.id} to cold`)
        })
    }
  }
  
  private async checkForPromotions(accessedMemories: TemporalMemory[]): Promise<void> {
    for (const memory of accessedMemories) {
      // Update access count
      memory.access_count += 1
      memory.t_accessed = new Date()
      
      // Check for promotion
      if (memory.access_count >= this.config.promotion_threshold && memory.memory_layer !== 'hot') {
        const oldLayer = memory.memory_layer
        memory.memory_layer = 'hot'
        console.log(`⬆️ Promoted memory ${memory.id}: ${oldLayer} → hot (${memory.access_count} accesses)`)
      }
    }
  }
  
  // Helper methods
  private getStoredMemoriesByLayer(layer: 'hot' | 'warm' | 'cold'): TemporalMemory[] {
    try {
      const allMemories = this.getAllStoredMemories()
      return allMemories.filter(memory => memory.memory_layer === layer)
    } catch (error) {
      console.error(`Error getting ${layer} memories:`, error)
      return []
    }
  }
  
  private getAllStoredMemories(): TemporalMemory[] {
    try {
      if (typeof window !== 'undefined' && window.localStorage) {
        const stored = localStorage.getItem('papertrail_temporal_memories')
        const memories = stored ? JSON.parse(stored) : []
        return memories.map((memory: any) => ({
          ...memory,
          t_created: new Date(memory.t_created),
          t_updated: new Date(memory.t_updated),
          t_accessed: new Date(memory.t_accessed),
          t_valid_from: new Date(memory.t_valid_from),
          t_valid_to: memory.t_valid_to ? new Date(memory.t_valid_to) : undefined,
        }))
      }
      return []
    } catch (error) {
      console.error('Error getting all stored memories:', error)
      return []
    }
  }
  
  private saveAllMemories(memories: TemporalMemory[]): void {
    try {
      if (typeof window !== 'undefined' && window.localStorage) {
        localStorage.setItem('papertrail_temporal_memories', JSON.stringify(memories))
      }
    } catch (error) {
      console.error('Error saving all memories:', error)
    }
  }
  
  private applyQueryFilters(memories: TemporalMemory[], query: Partial<MemoryQuery>): TemporalMemory[] {
    let filtered = memories
    
    if (query.content_query) {
      const queryLower = query.content_query.toLowerCase()
      filtered = filtered.filter(memory =>
        memory.content.toLowerCase().includes(queryLower)
      )
    }
    
    if (query.conversation_id) {
      filtered = filtered.filter(memory => 
        memory.conversation_id === query.conversation_id
      )
    }
    
    if (query.memory_type) {
      filtered = filtered.filter(memory => 
        memory.memory_type === query.memory_type
      )
    }
    
    if (query.min_confidence) {
      filtered = filtered.filter(memory => 
        memory.confidence >= query.min_confidence!
      )
    }
    
    // Sort by relevance (access time for now)
    filtered.sort((a, b) => 
      new Date(b.t_accessed).getTime() - new Date(a.t_accessed).getTime()
    )
    
    return filtered.slice(0, query.limit || 50)
  }
  
  private async simulateWarmAccess(): Promise<void> {
    // Simulate warm storage access delay
    const delay = 100 + Math.random() * 300 // 100-400ms
    await new Promise(resolve => setTimeout(resolve, delay))
  }
  
  private async simulateColdAccess(): Promise<void> {
    // Simulate cold storage access delay
    const delay = 500 + Math.random() * 1500 // 500-2000ms
    await new Promise(resolve => setTimeout(resolve, delay))
  }
  
  private getRecentAccesses(_layer: string): number {
    // Count recent accesses in the last hour
    const hourAgo = Date.now() - (60 * 60 * 1000)
    return Array.from(this.accessCache.values())
      .filter(time => time > hourAgo).length
  }
  
  private calculateCacheHitRate(layer: string): number {
    // Simulated cache hit rate
    return layer === 'warm' ? 0.75 : 0.45
  }
  
  private calculateCompressionRatio(): number {
    // Simulated compression ratio for cold storage
    return 0.3 // 70% compression
  }
}

// COMPLETELY DISABLE hierarchical memory service to prevent ALL issues
export const hierarchicalMemoryService = {
  getHotMemories: async () => [],
  getWarmMemories: async () => [],
  getColdMemories: async () => [],
  retrieveMemories: async () => ({ memories: [], performance: { total_time_ms: 0, layers_searched: [], cache_hits: 0, cache_misses: 0 } }),
  getLayerStatistics: async () => ({ hot: { count: 0, average_access_time_ms: 50, recent_accesses: 0 }, warm: { count: 0, average_access_time_ms: 200, cache_hit_rate: 0.75 }, cold: { count: 0, average_access_time_ms: 800, compression_ratio: 0.3 } })
}