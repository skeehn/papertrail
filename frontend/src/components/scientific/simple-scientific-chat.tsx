"use client"

import React, { useState } from 'react'
import { useChat } from '@ai-sdk/react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Card } from '@/components/ui/card'
import { Brain, Upload, RotateCcw, Send } from 'lucide-react'

export default function SimpleScientificChat() {
  const [showUpload, setShowUpload] = useState(false)
  
  const { messages, input, handleInputChange, handleSubmit, isLoading } = useChat() as any

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (input?.trim() && !isLoading) {
      handleSubmit(e)
    }
  }

  if (showUpload) {
    return (
      <div className="flex flex-col h-screen bg-gray-50">
        <div className="border-b bg-white px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Upload className="w-5 h-5 text-blue-500" />
              <h2 className="text-lg font-semibold">Upload Research Papers</h2>
            </div>
            <Button
              onClick={() => setShowUpload(false)}
              variant="outline"
              className="flex items-center gap-2"
            >
              <Brain className="w-4 h-4" />
              Back to Chat
            </Button>
          </div>
        </div>
        <div className="flex-1 p-6">
          <Card className="p-6 max-w-2xl mx-auto">
            <div className="text-center">
              <Upload className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium mb-2">Upload Scientific Papers</h3>
              <p className="text-gray-600 mb-6">
                Support for PDF files, DOI lookup, and arXiv integration coming soon.
              </p>
              <div className="grid gap-4">
                <Button variant="outline" disabled>
                  📄 Upload PDF
                </Button>
                <Button variant="outline" disabled>
                  🔗 Enter DOI
                </Button>
                <Button variant="outline" disabled>
                  📚 ArXiv URL
                </Button>
              </div>
            </div>
          </Card>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-screen bg-white">
      {/* Header */}
      <div className="border-b bg-gray-50 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Brain className="w-6 h-6 text-blue-500" />
            <h1 className="text-xl font-semibold">PaperTrail 2.0</h1>
          </div>
          <div className="flex gap-2">
            <Button
              onClick={() => setShowUpload(true)}
              variant="outline"
              size="sm"
              className="flex items-center gap-2"
            >
              <Upload className="w-4 h-4" />
              Upload
            </Button>
            <Button
              onClick={() => window.location.reload()}
              variant="outline"
              size="sm"
              className="flex items-center gap-2"
            >
              <RotateCcw className="w-4 h-4" />
              Clear
            </Button>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-4xl mx-auto space-y-6">
          {messages.length === 0 && (
            <Card className="p-6 text-center">
              <Brain className="w-12 h-12 text-blue-500 mx-auto mb-4" />
              <h2 className="text-xl font-semibold mb-2">Welcome to PaperTrail 2.0!</h2>
              <p className="text-gray-600 mb-6">
                I'm your intelligent research assistant. I can help you analyze scientific literature, 
                map arguments, and discover research insights.
              </p>
              <div className="text-left bg-gray-50 p-4 rounded-lg">
                <p className="text-sm font-medium text-gray-700 mb-2">Try asking me:</p>
                <ul className="text-sm text-gray-600 space-y-1">
                  <li>• "What papers do I have about machine learning?"</li>
                  <li>• "Find research on neural networks"</li>
                  <li>• "Show me claims about AI accuracy improvements"</li>
                  <li>• "Are there contradictions in my research collection?"</li>
                </ul>
              </div>
            </Card>
          )}

          {messages.map((message: any, index: number) => (
            <div
              key={message.id}
              className={`flex gap-3 ${
                message.role === 'user' ? 'justify-end' : 'justify-start'
              }`}
            >
              {message.role === 'assistant' && (
                <div className="w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center text-white text-sm font-medium">
                  AI
                </div>
              )}
              <div
                className={`max-w-3xl p-4 rounded-lg ${
                  message.role === 'user'
                    ? 'bg-blue-500 text-white'
                    : 'bg-gray-100 text-gray-900'
                }`}
              >
                <div className="prose prose-sm max-w-none">
                  {(message as any).content}
                </div>
              </div>
              {message.role === 'user' && (
                <div className="w-8 h-8 bg-gray-500 rounded-full flex items-center justify-center text-white text-sm font-medium">
                  {messages.length > 1 ? 'S' : 'U'}
                </div>
              )}
            </div>
          ))}

          {isLoading && (
            <div className="flex gap-3 justify-start">
              <div className="w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center text-white text-sm font-medium">
                AI
              </div>
              <div className="max-w-3xl p-4 rounded-lg bg-gray-100">
                <div className="flex items-center gap-2">
                  <div className="animate-spin w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full"></div>
                  <span className="text-gray-600">Thinking...</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Input */}
      <div className="border-t bg-white p-6">
        <form onSubmit={onSubmit} className="max-w-4xl mx-auto">
          <div className="flex gap-3">
            <Textarea
              value={input}
              onChange={handleInputChange}
              placeholder="Ask about research papers, upload documents, or explore scientific topics..."
              className="flex-1 min-h-[50px] resize-none"
              rows={2}
            />
            <Button
              type="submit"
              disabled={!input?.trim() || isLoading}
              className="px-6 flex items-center gap-2"
            >
              <Send className="w-4 h-4" />
              Send
            </Button>
          </div>
          <p className="text-xs text-gray-500 mt-2 text-center">
            I can search your papers, analyze claims, and provide research insights.
          </p>
        </form>
      </div>
    </div>
  )
}