import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import GraphVisualization from '@/components/graph/graph-visualization'

// Mock React Flow
vi.mock('@xyflow/react', () => ({
  ReactFlow: ({ children }: any) => <div data-testid="react-flow">{children}</div>,
  MiniMap: () => <div data-testid="minimap" />,
  Controls: () => <div data-testid="controls" />,
  Background: () => <div data-testid="background" />,
  Panel: ({ children }: any) => <div data-testid="panel">{children}</div>,
  useNodesState: () => [[], vi.fn(), vi.fn()],
  useEdgesState: () => [[], vi.fn(), vi.fn()],
  addEdge: vi.fn(),
}))

// Mock hooks
vi.mock('@/hooks/use-graph-data', () => ({
  useGraphQuery: () => ({ data: null }),
  useGraphStatistics: () => ({ data: null }),
}))

vi.mock('@/hooks/use-memory-persistence', () => ({
  useMemories: () => ({ data: [] }),
}))

describe('GraphVisualization', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders empty state when no data', () => {
    render(<GraphVisualization />)
    expect(screen.getByText(/No Knowledge Graph Data/i)).toBeInTheDocument()
  })

  it('renders graph when data is provided', () => {
    const mockData = {
      nodes: [
        { id: '1', label: 'Node 1', type: 'Entity', properties: {} },
      ],
      edges: [
        { source: '1', target: '2', type: 'RELATED_TO', properties: {} },
      ],
    }
    
    render(<GraphVisualization data={mockData} />)
    expect(screen.getByTestId('react-flow')).toBeInTheDocument()
  })
})
