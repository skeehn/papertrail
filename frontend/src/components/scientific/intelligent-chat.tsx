"use client"

import React, { useState, useEffect } from 'react'
import { useChat } from '@ai-sdk/react'
import { DefaultChatTransport } from 'ai'
import type { UIMessage } from 'ai'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { useConversationPersistence } from '@/hooks/use-memory-persistence'
import { 
  Send, 
  Brain,
  FileText,
  Search,
  Lightbulb,
  Network,
  MessageSquare,
  Upload
} from 'lucide-react'

interface IntelligentChatProps {
  papers: any[]
  className?: string
}

const IntelligentChat = ({ papers, className }: IntelligentChatProps) => {
  const [input, setInput] = useState("")
  const [lastSavedMessageCount, setLastSavedMessageCount] = useState(0)
  const [persistenceEnabled, setPersistenceEnabled] = useState(false)
  const { saveConversation, loadConversation } = useConversationPersistence()

  const { messages, sendMessage, status, error, setMessages } = useChat({
    transport: new DefaultChatTransport({
      api: "/api/scientific/intelligent-chat",
    }),
  })
  
  // Load persisted conversation on mount
  useEffect(() => {
    const persistedMessages = loadConversation()
    if (persistedMessages.length > 0) {
      setMessages(persistedMessages)
      setLastSavedMessageCount(persistedMessages.length)
    }
    // Enable persistence after initial load
    setTimeout(() => setPersistenceEnabled(true), 1000)
  }, [])

  // Save conversation when messages change
  useEffect(() => {
    if (!persistenceEnabled) return
    
    if (messages.length > 0 && messages.length !== lastSavedMessageCount) {
      setLastSavedMessageCount(messages.length)
      
      const timeoutId = setTimeout(async () => {
        try {
          await saveConversation(messages)
          console.log('💾 Scientific conversation saved:', messages.length, 'messages')
        } catch (error) {
          console.error('Failed to save conversation:', error)
        }
      }, 1000)
      
      return () => clearTimeout(timeoutId)
    }
  }, [messages.length, persistenceEnabled, saveConversation])

  const handleSubmit = () => {
    if (!input.trim()) return

    sendMessage({ text: input })
    setInput("")
  }

  const suggestionQuestions = [
    "What papers do I have about machine learning?",
    "Find research on neural networks",
    "Show me claims about AI accuracy improvements", 
    "What are the main research topics in my collection?",
    "Are there any contradicting findings in my papers?",
    "Summarize the key insights from all papers"
  ]

  const handleSuggestionClick = (suggestion: string) => {
    setInput(suggestion)
  }

  return (
    <div className={`h-full flex flex-col ${className}`}>
      {/* Header */}
      <div className="border-b p-4 bg-white">
        <div className="flex items-center gap-2 mb-2">
          <Brain className="w-5 h-5 text-blue-500" />
          <h3 className="font-semibold">Intelligent Research Assistant</h3>
        </div>
        <p className="text-sm text-gray-600">
          Ask me about your papers, research topics, or scientific concepts
        </p>
        {papers.length > 0 && (
          <div className="mt-2">
            <Badge variant="outline" className="text-xs">
              {papers.length} papers • {papers.reduce((sum, p) => sum + (p.claims?.length || 0), 0)} claims loaded
            </Badge>
          </div>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="space-y-4">
            {/* Welcome message */}
            <Card className="p-4">
              <div className="flex items-start gap-3">
                <Brain className="w-5 h-5 text-blue-500 mt-0.5" />
                <div>
                  <p className="text-sm mb-3">
                    I&apos;m your intelligent research assistant. I can help you explore your paper collection, 
                    find specific topics, analyze claims, and discover connections between research.
                  </p>
                  <div className="flex items-center gap-2 text-xs text-gray-500">
                    <FileText className="w-3 h-3" />
                    <span>I have access to {papers.length} papers in your collection</span>
                  </div>
                </div>
              </div>
            </Card>
            
            {/* Suggestion buttons */}
            <div className="space-y-2">
              <p className="text-sm font-medium text-gray-700">Try asking:</p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {suggestionQuestions.map((question, index) => (
                  <Button
                    key={index}
                    variant="outline"
                    size="sm"
                    onClick={() => handleSuggestionClick(question)}
                    className="text-left justify-start h-auto p-3 text-xs"
                  >
                    <MessageSquare className="w-3 h-3 mr-2 flex-shrink-0" />
                    <span>{question}</span>
                  </Button>
                ))}
              </div>
            </div>

            {papers.length === 0 && (
              <Card className="p-4 border-dashed">
                <div className="text-center">
                  <Upload className="w-8 h-8 mx-auto text-gray-300 mb-2" />
                  <p className="text-sm text-gray-500">
                    Upload some papers first, then I can help you analyze and explore them
                  </p>
                </div>
              </Card>
            )}
          </div>
        )}

        {messages.map(message => (
          <div key={message.id} className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            {message.role === 'assistant' ? (
              <Card className="max-w-[85%] p-4">
                <div className="flex items-start gap-3">
                  <Brain className="w-5 h-5 text-blue-500 mt-0.5 flex-shrink-0" />
                  <div className="flex-1">
                    <div className="prose prose-sm max-w-none">
                      {message.parts
                        .map((part) => (part.type === "text" ? part.text : null))
                        .join("")}
                    </div>
                  </div>
                </div>
              </Card>
            ) : (
              <div className="max-w-[85%] bg-blue-500 text-white p-3 rounded-lg">
                {message.parts
                  .map((part) => (part.type === "text" ? part.text : null))
                  .join("")}
              </div>
            )}
          </div>
        ))}
        
        {status === "submitted" && (
          <div className="flex justify-start">
            <Card className="p-4">
              <div className="flex items-center gap-3">
                <Brain className="w-5 h-5 text-blue-500 animate-pulse" />
                <div className="text-sm text-gray-600">
                  Searching through your papers and analyzing...
                </div>
              </div>
            </Card>
          </div>
        )}

        {status === "error" && error && (
          <Card className="p-4 border-red-200 bg-red-50">
            <div className="flex items-center gap-2">
              <div className="text-red-600 text-sm">
                Error: {error.message}
              </div>
            </div>
          </Card>
        )}
      </div>

      {/* Input */}
      <div className="border-t p-4 bg-white">
        <div className="flex gap-2">
          <Input
            placeholder="Ask about your research papers, topics, or scientific concepts..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSubmit()}
            disabled={status === "submitted"}
          />
          <Button onClick={handleSubmit} disabled={!input.trim() || status === "submitted"}>
            <Send className="w-4 h-4" />
          </Button>
        </div>
        
        {input && (
          <div className="mt-2 text-xs text-gray-500">
            I&apos;ll search through {papers.length} papers and {papers.reduce((sum, p) => sum + (p.claims?.length || 0), 0)} claims to answer your question
          </div>
        )}
      </div>
    </div>
  )
}

export default IntelligentChat