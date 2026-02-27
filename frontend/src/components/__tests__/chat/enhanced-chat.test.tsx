import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import EnhancedChat from '@/components/chat/enhanced-chat'

// Mock the useAgentChat hook
vi.mock('@/hooks/use-agent-chat', () => ({
  useAgentChat: () => ({
    messages: [],
    isLoading: false,
    error: null,
    selectedAgent: 'synthesizer',
    setSelectedAgent: vi.fn(),
    sendMessage: vi.fn(),
    clearMessages: vi.fn(),
  }),
}))

// Mock the useWebSocket hook
vi.mock('@/hooks/use-websocket', () => ({
  useWebSocket: () => ({
    isConnected: false,
    connectionId: null,
    sendMessage: vi.fn(),
    subscribe: vi.fn(),
    unsubscribe: vi.fn(),
    lastMessage: null,
    error: null,
    connect: vi.fn(),
    disconnect: vi.fn(),
  }),
}))

describe('EnhancedChat', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders welcome message when no messages', () => {
    render(<EnhancedChat />)
    expect(screen.getByText(/Welcome to PaperTrail/i)).toBeInTheDocument()
  })

  it('renders file upload button', () => {
    render(<EnhancedChat />)
    const uploadButton = screen.getByRole('button', { name: /upload/i })
    expect(uploadButton).toBeInTheDocument()
  })

  it('renders agent selector', () => {
    render(<EnhancedChat />)
    // Agent selector uses buttons for each agent type
    expect(screen.getByRole('button', { name: /synthesizer/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /critic/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /connector/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /reasoning/i })).toBeInTheDocument()
  })

  it('renders input textarea', () => {
    render(<EnhancedChat />)
    const textarea = screen.getByPlaceholderText(/Ask about your research papers/i)
    expect(textarea).toBeInTheDocument()
  })
})
