"use client"

import React, { useState } from 'react'
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
  Eye
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { PaperCardSkeleton } from '@/components/ui/loading-skeleton'

interface Paper {
  id: string
  title: string
  authors: string[]
  uploadDate: Date
  status: 'processed' | 'processing' | 'failed'
  tags: string[]
  thumbnail?: string
  pageCount?: number
}

// Mock data
const mockPapers: Paper[] = [
  {
    id: '1',
    title: 'Attention Is All You Need',
    authors: ['Vaswani et al.'],
    uploadDate: new Date(2024, 0, 15),
    status: 'processed',
    tags: ['Deep Learning', 'NLP', 'Transformers']
  },
  {
    id: '2',
    title: 'Deep Residual Learning for Image Recognition',
    authors: ['He et al.'],
    uploadDate: new Date(2024, 0, 10),
    status: 'processed',
    tags: ['Computer Vision', 'ResNet']
  },
  {
    id: '3',
    title: 'BERT: Pre-training of Deep Bidirectional Transformers',
    authors: ['Devlin et al.'],
    uploadDate: new Date(2024, 0, 5),
    status: 'processing',
    tags: ['NLP', 'BERT', 'Pre-training']
  }
]

export default function PapersLibraryContent() {
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid')
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedTags, setSelectedTags] = useState<string[]>([])
  const [papers] = useState<Paper[]>(mockPapers)
  const [isLoading] = useState(false)

  const filteredPapers = papers.filter(paper =>
    (searchQuery === '' ||
      paper.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      paper.authors.some(a => a.toLowerCase().includes(searchQuery.toLowerCase()))) &&
    (selectedTags.length === 0 ||
      selectedTags.some(tag => paper.tags.includes(tag)))
  )

  const allTags = Array.from(new Set(papers.flatMap(p => p.tags)))

  const PaperGridCard = ({ paper }: { paper: Paper }) => (
    <Card className="p-4 hover:shadow-md transition-all duration-200 group">
      <div className="space-y-3">
        <div className="flex gap-3">
          <div className="w-12 h-16 bg-muted rounded flex items-center justify-center flex-shrink-0">
            <FileText className="w-6 h-6 text-muted-foreground" />
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="font-medium text-sm line-clamp-2 mb-1">{paper.title}</h3>
            <p className="text-xs text-muted-foreground">{paper.authors.join(', ')}</p>
          </div>
        </div>

        <div className="flex flex-wrap gap-1.5">
          {paper.tags.map(tag => (
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
            {paper.uploadDate.toLocaleDateString()}
          </div>
          <span className={cn(
            'px-2 py-0.5 rounded-full text-xs font-medium',
            paper.status === 'processed' && 'bg-green-100 text-green-700',
            paper.status === 'processing' && 'bg-yellow-100 text-yellow-700',
            paper.status === 'failed' && 'bg-red-100 text-red-700'
          )}>
            {paper.status}
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
          <Button size="sm" variant="ghost">
            <Trash2 className="w-3 h-3" />
          </Button>
        </div>
      </div>
    </Card>
  )

  const PaperListItem = ({ paper }: { paper: Paper }) => (
    <Card className="p-4 hover:shadow-sm transition-all duration-200 group">
      <div className="flex items-center gap-4">
        <div className="w-10 h-14 bg-muted rounded flex items-center justify-center flex-shrink-0">
          <FileText className="w-5 h-5 text-muted-foreground" />
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="font-medium text-sm mb-1">{paper.title}</h3>
          <div className="flex items-center gap-4 text-xs text-muted-foreground">
            <span className="flex items-center gap-1">
              <User className="w-3 h-3" />
              {paper.authors[0]}
            </span>
            <span className="flex items-center gap-1">
              <Calendar className="w-3 h-3" />
              {paper.uploadDate.toLocaleDateString()}
            </span>
          </div>
        </div>
        <div className="flex flex-wrap gap-1.5 max-w-xs">
          {paper.tags.slice(0, 3).map(tag => (
            <span
              key={tag}
              className="text-xs px-2 py-0.5 bg-primary-50 text-primary-700 rounded-full"
            >
              {tag}
            </span>
          ))}
        </div>
        <span className={cn(
          'px-3 py-1 rounded-full text-xs font-medium flex-shrink-0',
          paper.status === 'processed' && 'bg-green-100 text-green-700',
          paper.status === 'processing' && 'bg-yellow-100 text-yellow-700',
          paper.status === 'failed' && 'bg-red-100 text-red-700'
        )}>
          {paper.status}
        </span>
        <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
          <Button size="sm" variant="outline">
            <Eye className="w-3 h-3 mr-1" />
            View
          </Button>
          <Button size="sm" variant="ghost">
            <Download className="w-3 h-3" />
          </Button>
          <Button size="sm" variant="ghost">
            <Trash2 className="w-3 h-3" />
          </Button>
        </div>
      </div>
    </Card>
  )

  return (
    <div className="space-y-6">
      {/* Toolbar */}
      <div className="flex flex-col md:flex-row gap-4">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            placeholder="Search papers by title, author..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10"
          />
        </div>
        <div className="flex gap-2">
          <Button variant="outline">
            <Filter className="w-4 h-4 mr-2" />
            Filters
          </Button>
          <div className="flex border rounded-lg p-1">
            <Button
              size="sm"
              variant={viewMode === 'grid' ? 'secondary' : 'ghost'}
              onClick={() => setViewMode('grid')}
              className="h-8"
            >
              <Grid3x3 className="w-4 h-4" />
            </Button>
            <Button
              size="sm"
              variant={viewMode === 'list' ? 'secondary' : 'ghost'}
              onClick={() => setViewMode('list')}
              className="h-8"
            >
              <List className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </div>

      {/* Tags Filter */}
      {allTags.length > 0 && (
        <div className="flex flex-wrap gap-2">
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
                'text-xs px-3 py-1 rounded-full transition-colors',
                selectedTags.includes(tag)
                  ? 'bg-primary-600 text-white'
                  : 'bg-muted hover:bg-muted/70'
              )}
            >
              <Tag className="w-3 h-3 inline mr-1" />
              {tag}
            </button>
          ))}
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
        <Card className="p-12 text-center">
          <div className="max-w-md mx-auto">
            <div className="w-16 h-16 bg-muted rounded-full flex items-center justify-center mx-auto mb-4">
              <FileText className="w-8 h-8 text-muted-foreground" />
            </div>
            <h3 className="text-xl font-semibold mb-2">
              {searchQuery || selectedTags.length > 0 ? 'No papers found' : 'No papers yet'}
            </h3>
            <p className="text-muted-foreground mb-6">
              {searchQuery || selectedTags.length > 0
                ? 'Try adjusting your search or filters'
                : 'Upload your first research paper to get started with PaperTrail'}
            </p>
            {!searchQuery && selectedTags.length === 0 && (
              <Button>
                <Upload className="w-4 h-4 mr-2" />
                Upload Your First Paper
              </Button>
            )}
          </div>
        </Card>
      ) : (
        <div className={cn(
          viewMode === 'grid'
            ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4'
            : 'space-y-3'
        )}>
          {filteredPapers.map(paper =>
            viewMode === 'grid' ? (
              <PaperGridCard key={paper.id} paper={paper} />
            ) : (
              <PaperListItem key={paper.id} paper={paper} />
            )
          )}
        </div>
      )}
    </div>
  )
}
