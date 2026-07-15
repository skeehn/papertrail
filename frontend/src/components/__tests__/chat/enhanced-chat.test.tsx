import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import EnhancedChat from '@/components/chat/enhanced-chat'
import { CHAT_MODELS } from '@/lib/chat-models'

const sendMessage = vi.fn()

// The chat streams via the AI SDK; stub the hook so tests stay offline.
vi.mock('@ai-sdk/react', () => ({
  useChat: () => ({
    messages: [],
    sendMessage,
    status: 'ready',
    error: undefined,
    stop: vi.fn(),
    setMessages: vi.fn(),
  }),
}))

vi.mock('ai', () => ({
  DefaultChatTransport: class {
    constructor(_opts: unknown) {}
  },
}))

describe('EnhancedChat', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders the welcome state', () => {
    render(<EnhancedChat />)
    expect(screen.getByText(/Welcome to/i)).toBeInTheDocument()
    expect(
      screen.getByPlaceholderText(/Ask about your research papers/i)
    ).toBeInTheDocument()
  })

  it('shows the model picker with the default model', () => {
    render(<EnhancedChat />)
    expect(
      screen.getByRole('button', { name: new RegExp(CHAT_MODELS[0].label, 'i') })
    ).toBeInTheDocument()
  })

  it('lists every available model when the picker is opened', () => {
    render(<EnhancedChat />)
    fireEvent.click(
      screen.getByRole('button', { name: new RegExp(CHAT_MODELS[0].label, 'i') })
    )
    CHAT_MODELS.forEach((m) => {
      expect(screen.getAllByText(m.label).length).toBeGreaterThan(0)
    })
  })

  it('disables send until the user types, then sends the message', () => {
    render(<EnhancedChat />)
    const send = screen.getByRole('button', { name: /send message/i })
    expect(send).toBeDisabled()

    fireEvent.change(screen.getByPlaceholderText(/Ask about your research papers/i), {
      target: { value: 'what papers do I have?' },
    })
    expect(send).not.toBeDisabled()

    fireEvent.click(send)
    expect(sendMessage).toHaveBeenCalledWith(
      { text: 'what papers do I have?' },
      { body: { modelId: CHAT_MODELS[0].id } }
    )
  })

  it('offers an attach control for PDFs', () => {
    render(<EnhancedChat />)
    expect(screen.getByRole('button', { name: /attach/i })).toBeInTheDocument()
  })
})
