"use client"

import React, { useState, memo, useMemo } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card } from '@/components/ui/card'
import {
  Upload,
  Search,
  Filter,
  Grid3x3,
  List,
  FileText,
  Calendar,
  User,
  Tag,
  Download,
  Trash2,
  Eye,
  X,
  Sparkles
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { PaperCardSkeleton } from '@/components/ui/loading-skeleton'
import { usePapers } from '@/hooks/use-papers'
import type { Paper } from '@/hooks/use-papers'

const PapersLibraryContent = memo(function PapersLibraryContent() {
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid')
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedTags, setSelectedTags] = useState<string[]>([])
  const [searchSuggestions, setSearchSuggestions] = useState<string[]>([])
  const [showSuggestions, setShowSuggestions] = useState(false)
  const { papers, isLoading, error, deletePaper } = usePapers(searchQuery)

  const filteredPapers = useMemo(() => {
    return papers.filter(paper =>
      (searchQuery === '' ||
        paper.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        paper.authors.some(a => a.toLowerCase().includes(searchQuery.toLowerCase())) ||
        paper.abstract?.toLowerCase().includes(searchQuery.toLowerCase())) &&
      (selectedTags.length === 0 ||
        selectedTags.some(tag => paper.tags?.includes(tag)))
    )
  }, [papers, searchQuery, selectedTags])

  const allTags = useMemo(() => Array.from(new Set(papers.flatMap(p => p.tags || []))), [papers])

  // Generate search suggestions based on papers
  const generateSuggestions = useMemo(() => {
    if (!searchQuery || searchQuery.length < 2) return []
    const queryLower = searchQuery.toLowerCase()
    const suggestions = new Set<string>()
    
    papers.forEach(paper => {
      if (paper.title.toLowerCase().includes(queryLower)) {
        suggestions.add(paper.title)
      }
      paper.authors.forEach(author => {
        if (author.toLowerCase().includes(queryLower)) {
          suggestions.add(author)
        }
      })
      paper.tags?.forEach(tag => {
        if (tag.toLowerCase().includes(queryLower)) {
          suggestions.add(tag)
        }
      })
    })
    
    return Array.from(suggestions).slice(0, 5)
  }, [searchQuery, papers])

  const handleSearchChange = (value: string) => {
    setSearchQuery(value)
    if (value.length >= 2) {
      setSearchSuggestions(generateSuggestions)
      setShowSuggestions(true)
    } else {
      setShowSuggestions(false)
    }
  }

  const highlightText = (text: string, query: string) => {
    if (!query) return text
    const parts = text.split(new RegExp(`(${query})`, 'gi'))
    return parts.map((part, i) => 
      part.toLowerCase() === query.toLowerCase() ? (
        <mark key={i} className="bg-yellow-200 dark:bg-yellow-900 px-0.5 rounded">
          {part}
        </mark>
      ) : part
    )
  }

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation()
    if (confirm('Are you sure you want to delete this paper?')) {
      try {
        await deletePaper(id)
      } catch (err) {
        console.error('Failed to delete paper:', err)
      }
    }
  }

  const handleUpload = () => {
    window.location.href = '/'
  }

  const PaperGridCard = ({ paper }: { paper: Paper }) => (
    <Card className="p-4 hover:shadow-lg transition-all duration-200 group hover:scale-[1.02] border hover:border-primary/20">
      <div className="space-y-3">
        <div className="flex gap-3">
          <div className="w-12 h-16 bg-gradient-to-br from-primary-500/10 to-primary-600/10 rounded flex items-center justify-center flex-shrink-0 group-hover:from-primary-500/20 group-hover:to-primary-600/20 transition-colors">
            <FileText className="w-6 h-6 text-primary-600" />
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="font-medium text-sm line-clamp-2 mb-1 group-hover:text-primary-600 transition-colors">
              {searchQuery ? highlightText(paper.title, searchQuery) : paper.title}
            </h3>
            <p className="text-xs text-muted-foreground line-clamp-1">
              {paper.authors.join(', ')}
            </p>
          </div>
        </div>

        <div className="flex flex-wrap gap-1.5">
          {(paper.tags || []).map(tag => (
            <span
              key={tag}
              className="text-xs px-2 py-0.5 bg-primary-50 text-primary-700 rounded-full"
            >
              {tag}
            </span>
          ))}
        </div>

        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <div className="flex items-center gap-1">
            <Calendar className="w-3 h-3" />
            {paper.uploadDate || paper.created_at ? new Date(paper.uploadDate || paper.created_at || '').toLocaleDateString() : 'N/A'}
          </div>
          <span className={cn(
            'px-2 py-0.5 rounded-full text-xs font-medium',
            paper.status === 'processed' && 'bg-green-100 text-green-700',
            paper.status === 'processing' && 'bg-yellow-100 text-yellow-700',
            paper.status === 'pending' && 'bg-blue-100 text-blue-700',
            paper.status === 'failed' && 'bg-red-100 text-red-700'
          )}>
            {paper.status || 'Unknown'}
          </span>
        </div>

        <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
          <Button size="sm" variant="outline" className="flex-1">
            <Eye className="w-3 h-3 mr-1" />
            View
          </Button>
          <Button size="sm" variant="ghost">
            <Download className="w-3 h-3" />
          </Button>
          <Button size="sm" variant="ghost" onClick={(e) => handleDelete(paper.id, e)}>
            <Trash2 className="w-3 h-3" />
          </Button>
        </div>
      </div>
    </Card>
  )

  const PaperListItem = ({ paper }: { paper: Paper }) => (
    <Card className="p-4 hover:bg-muted/30 transition-colors group border border-border/50">
      <div className="flex items-center gap-4">
        <div className="w-10 h-14 bg-muted rounded flex items-center justify-center flex-shrink-0">
          <FileText className="w-5 h-5 text-foreground" />
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="font-medium text-sm mb-1">
            {searchQuery ? highlightText(paper.title, searchQuery) : paper.title}
          </h3>
          <div className="flex items-center gap-4 text-xs text-muted-foreground">
            <span className="flex items-center gap-1">
              <User className="w-3 h-3" />
              {paper.authors[0]}
            </span>
            <span className="flex items-center gap-1">
              <Calendar className="w-3 h-3" />
              {paper.uploadDate || paper.created_at ? new Date(paper.uploadDate || paper.created_at || '').toLocaleDateString() : 'N/A'}
            </span>
          </div>
        </div>
        <div className="flex flex-wrap gap-1.5 max-w-xs">
          {(paper.tags || []).slice(0, 3).map(tag => (
            <span
              key={tag}
              className="text-xs px-2 py-0.5 bg-muted text-foreground rounded"
            >
              {tag}
            </span>
          ))}
          {(paper.tags || []).length > 3 && (
            <span className="text-xs px-2 py-0.5 text-muted-foreground">
              +{(paper.tags || []).length - 3}
            </span>
          )}
        </div>
        <span className="text-xs text-muted-foreground flex-shrink-0">
          {paper.status || 'Unknown'}
        </span>
        <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
          <Button size="sm" variant="outline">
            <Eye className="w-3 h-3 mr-1" />
            View
          </Button>
          <Button size="sm" variant="ghost">
            <Download className="w-3 h-3" />
          </Button>
          <Button size="sm" variant="ghost" onClick={(e) => handleDelete(paper.id, e)}>
            <Trash2 className="w-3 h-3" />
          </Button>
        </div>
      </div>
    </Card>
  )

  return (
    <div className="space-y-6">
      {error && (
        <Card className="p-4 bg-destructive/10 border-destructive">
          <p className="text-sm text-destructive">{error}</p>
          <Button size="sm" onClick={() => window.location.reload()} className="mt-2">
            Retry
          </Button>
        </Card>
      )}

      {/* Toolbar */}
      <div className="flex flex-col md:flex-row gap-4">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground z-10" />
          <Input
            placeholder="Search papers by title, author..."
            value={searchQuery}
            onChange={(e) => handleSearchChange(e.target.value)}
            onFocus={() => {
              if (searchQuery.length >= 2) {
                setShowSuggestions(true)
              }
            }}
            onBlur={() => {
              // Delay to allow clicking on suggestions
              setTimeout(() => setShowSuggestions(false), 200)
            }}
            className="pl-10 pr-4"
          />
          {/* Autocomplete Suggestions */}
          {showSuggestions && searchSuggestions.length > 0 && (
            <div className="absolute top-full left-0 right-0 mt-1 bg-card border rounded-lg shadow-lg z-50 max-h-60 overflow-y-auto">
              {searchSuggestions.map((suggestion, index) => (
                <button
                  key={index}
                  onClick={() => {
                    setSearchQuery(suggestion)
                    setShowSuggestions(false)
                  }}
                  className="w-full text-left px-4 py-2 text-sm hover:bg-muted transition-colors flex items-center gap-2"
                >
                  <Sparkles className="w-3 h-3 text-muted-foreground" />
                  <span>{suggestion}</span>
                </button>
              ))}
            </div>
          )}
        </div>
        <div className="flex gap-2">
          <Button variant="outline" className="transition-all hover:bg-muted">
            <Filter className="w-4 h-4 mr-2" />
            Filters
          </Button>
          <div className="flex border rounded-lg p-1 bg-muted/30">
            <Button
              size="sm"
              variant={viewMode === 'grid' ? 'secondary' : 'ghost'}
              aria-label="Grid view"
              onClick={() => setViewMode('grid')}
              className="h-8 transition-all"
            >
              <Grid3x3 className="w-4 h-4" />
            </Button>
            <Button
              size="sm"
              variant={viewMode === 'list' ? 'secondary' : 'ghost'}
              aria-label="List view"
              onClick={() => setViewMode('list')}
              className="h-8 transition-all"
            >
              <List className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </div>

      {/* Tags Filter */}
      {allTags.length > 0 && (
        <div className="flex flex-wrap gap-2 items-center">
          <span className="text-sm font-medium text-muted-foreground">Tags:</span>
          {allTags.map(tag => (
            <button
              key={tag}
              onClick={() => {
                setSelectedTags(prev =>
                  prev.includes(tag)
                    ? prev.filter(t => t !== tag)
                    : [...prev, tag]
                )
              }}
              className={cn(
                'text-xs px-3 py-1.5 rounded transition-colors flex items-center gap-1.5',
                selectedTags.includes(tag)
                  ? 'bg-foreground text-background'
                  : 'bg-muted hover:bg-muted/80 text-foreground'
              )}
            >
              <Tag className="w-3 h-3" />
              {tag}
            </button>
          ))}
          {selectedTags.length > 0 && (
            <button
              onClick={() => setSelectedTags([])}
              className="text-xs px-2 py-1 text-muted-foreground hover:text-foreground transition-colors flex items-center gap-1"
            >
              <X className="w-3 h-3" />
              Clear
            </button>
          )}
        </div>
      )}

      {/* Papers Grid/List */}
      {isLoading ? (
        <div className={cn(
          viewMode === 'grid'
            ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4'
            : 'space-y-3'
        )}>
          {[1, 2, 3, 4, 5, 6].map(i => (
            <PaperCardSkeleton key={i} />
          ))}
        </div>
      ) : filteredPapers.length === 0 ? (
        <Card className="p-12 text-center border border-border/50">
          <div className="max-w-md mx-auto space-y-6">
            <div className="w-16 h-16 bg-muted rounded-full flex items-center justify-center mx-auto">
              <FileText className="w-8 h-8 text-foreground" />
            </div>
            <div className="space-y-2">
              <h3 className="text-xl font-semibold text-foreground">
                {searchQuery || selectedTags.length > 0 ? 'No papers found' : 'No papers yet'}
              </h3>
              <p className="text-muted-foreground">
                {searchQuery || selectedTags.length > 0
                  ? 'Try adjusting your search or filters'
                  : 'Upload your first research paper to get started with PaperTrail'}
              </p>
            </div>
            {!searchQuery && selectedTags.length === 0 && (
              <Button onClick={handleUpload} className="mt-4 bg-foreground text-background hover:bg-foreground/90">
                <Upload className="w-4 h-4 mr-2" />
                Upload Your First Paper
              </Button>
            )}
            {(searchQuery || selectedTags.length > 0) && (
              <Button 
                variant="outline" 
                onClick={() => {
                  setSearchQuery('')
                  setSelectedTags([])
                }}
                className="mt-2"
              >
                <X className="w-4 h-4 mr-2" />
                Clear Filters
              </Button>
            )}
          </div>
        </Card>
      ) : (
        <div className={cn(
          viewMode === 'grid'
            ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4'
            : 'space-y-3',
          'animate-in fade-in duration-500'
        )}>
          {filteredPapers.map((paper, index) =>
            viewMode === 'grid' ? (
              <div
                key={paper.id}
                className="animate-in fade-in slide-in-from-bottom-4"
                style={{ '--animation-delay': index * 50 } as React.CSSProperties}
              >
                <PaperGridCard paper={paper} />
              </div>
            ) : (
              <div
                key={paper.id}
                className="animate-in fade-in slide-in-from-left-4"
                style={{ '--animation-delay': index * 30 } as React.CSSProperties}
              >
                <PaperListItem paper={paper} />
              </div>
            )
          )}
        </div>
      )}

      {/* Results count */}
      {!isLoading && filteredPapers.length > 0 && (
        <div className="mt-6 text-center text-sm text-muted-foreground">
          Showing {filteredPapers.length} of {papers.length} paper{filteredPapers.length !== 1 ? 's' : ''}
          {(searchQuery || selectedTags.length > 0) && (
            <span className="ml-2">
              (filtered from {papers.length} total)
            </span>
          )}
        </div>
      )}
    </div>
  )
})

export default PapersLibraryContent
