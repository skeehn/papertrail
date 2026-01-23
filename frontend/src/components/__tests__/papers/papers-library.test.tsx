import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import PapersLibraryContent from '@/app/papers/papers-library'

// Mock the usePapers hook
vi.mock('@/hooks/use-papers', () => ({
  usePapers: () => ({
    papers: [
      {
        id: '1',
        title: 'Test Paper',
        authors: ['Author One'],
        status: 'processed',
        tags: ['AI', 'ML'],
      },
    ],
    isLoading: false,
    error: null,
    refetch: vi.fn(),
    deletePaper: vi.fn(),
  }),
}))

describe('PapersLibraryContent', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders papers list', async () => {
    render(<PapersLibraryContent />)
    await waitFor(() => {
      expect(screen.getByText('Test Paper')).toBeInTheDocument()
    })
  })

  it('renders search input', () => {
    render(<PapersLibraryContent />)
    const searchInput = screen.getByPlaceholderText(/Search papers/i)
    expect(searchInput).toBeInTheDocument()
  })

  it('renders view mode toggle', () => {
    render(<PapersLibraryContent />)
    const gridButton = screen.getByRole('button', { name: /grid/i })
    expect(gridButton).toBeInTheDocument()
  })
})
