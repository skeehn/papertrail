import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'

export interface Paper {
  id: string
  title: string
  authors: string[]
  uploadDate?: string
  created_at?: string
  status?: 'processed' | 'processing' | 'pending' | 'failed'
  tags?: string[]
  arxiv_id?: string
  filename?: string
  abstract?: string
  pageCount?: number
}

interface UsePapersReturn {
  papers: Paper[]
  isLoading: boolean
  error: string | null
  refetch: () => void
  deletePaper: (id: string) => Promise<void>
}

export function usePapers(searchQuery?: string): UsePapersReturn {
  const queryClient = useQueryClient()

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['papers', searchQuery],
    queryFn: async () => {
      const url = new URL('/api/papers/list', window.location.origin)
      if (searchQuery) {
        url.searchParams.set('search', searchQuery)
      }
      const response = await fetch(url.toString())
      if (!response.ok) {
        throw new Error('Failed to fetch papers')
      }
      const data = await response.json()
      // Handle both response formats: {papers: [...]} and direct array
      const papersList = Array.isArray(data) ? data : (data.papers || [])
      // Transform backend format to frontend format
      return papersList.map((paper: any) => ({
        id: paper.id || paper.paper_id || String(Date.now()),
        title: paper.title || paper.filename || 'Untitled Paper',
        authors: Array.isArray(paper.authors) ? paper.authors : (paper.authors ? [paper.authors] : []),
        uploadDate: paper.upload_date || paper.created_at || paper.uploadDate,
        created_at: paper.created_at || paper.upload_date,
        status: paper.status || 'processed',
        tags: paper.tags || [],
        arxiv_id: paper.arxiv_id,
        filename: paper.filename,
        abstract: paper.abstract,
        pageCount: paper.page_count || paper.pageCount,
      })) as Paper[]
    },
    staleTime: 30000, // Consider data fresh for 30 seconds
    gcTime: 300000, // Keep in cache for 5 minutes
  })

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      const response = await fetch(`/api/papers/${id}`, {
        method: 'DELETE',
      })
      if (!response.ok) {
        throw new Error('Failed to delete paper')
      }
    },
    onSuccess: () => {
      // Invalidate and refetch papers list
      queryClient.invalidateQueries({ queryKey: ['papers'] })
    },
  })

  return {
    papers: data ?? [],
    isLoading,
    error: error instanceof Error ? error.message : null,
    refetch: () => queryClient.invalidateQueries({ queryKey: ['papers'] }),
    deletePaper: deleteMutation.mutateAsync,
  }
}
