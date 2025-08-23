"use client"

import React, { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { 
  Send, 
  Brain,
  Search,
  AlertTriangle,
  Lightbulb,
  Link2,
  FileText
} from 'lucide-react'

interface ScientificChatProps {
  papers: any[]
  selectedPaper: any
}

interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  type?: 'summary' | 'critique' | 'connection' | 'question'
  citations?: string[]
  confidence?: number
}

const ScientificChat = ({ papers, selectedPaper }: ScientificChatProps) => {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const handleSend = async () => {
    if (!input.trim() || !selectedPaper) return

    const userMessage: ChatMessage = {
      id: `msg_${Date.now()}`,
      role: 'user',
      content: input
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsLoading(true)

    try {
      // Simulate scientific agent response
      const response = await simulateScientificResponse(input, selectedPaper, papers)
      
      setMessages(prev => [...prev, response])
    } catch (error) {
      console.error('Scientific chat error:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const simulateScientificResponse = async (query: string, paper: any, allPapers: any[]): Promise<ChatMessage> => {
    // Simulate processing time
    await new Promise(resolve => setTimeout(resolve, 2000))

    const queryLower = query.toLowerCase()
    
    // Determine response type based on query
    if (queryLower.includes('summarize') || queryLower.includes('summary')) {
      return {
        id: `msg_${Date.now()}`,
        role: 'assistant',
        content: `**Summary of "${paper.title}"**\n\nThis paper presents ${paper.claims.length} key claims about ${paper.entities.slice(0, 2).map((e: any) => e.text).join(' and ')}. The main finding is that ${paper.claims[0]?.text || 'machine learning techniques show significant improvements'}.\n\n**Key Claims:**\n${paper.claims.slice(0, 3).map((claim: any, i: number) => `${i + 1}. ${claim.text} (confidence: ${claim.confidence})`).join('\n')}`,
        type: 'summary',
        citations: [paper.id],
        confidence: 0.92
      }
    }
    
    if (queryLower.includes('critique') || queryLower.includes('weakness') || queryLower.includes('limitation')) {
      return {
        id: `msg_${Date.now()}`,
        role: 'assistant',
        content: `**Critical Analysis of "${paper.title}"**\n\n⚠️ **Potential Limitations:**\n\n1. **Sample Size**: The study may benefit from larger datasets\n2. **Methodological Concerns**: The approach shows ${paper.claims.filter((c: any) => c.modality === 'weak').length} weak claims that need stronger evidence\n3. **Reproducibility**: Some claims lack sufficient methodological detail\n\n**Contradictions Found:**\n- Claim "${paper.claims[0]?.text}" conflicts with established findings in the field\n- Evidence strength varies significantly across different claims`,
        type: 'critique',
        citations: [paper.id],
        confidence: 0.78
      }
    }
    
    if (queryLower.includes('connect') || queryLower.includes('related') || queryLower.includes('similar')) {
      return {
        id: `msg_${Date.now()}`,
        role: 'assistant',
        content: `**Related Work Connections**\n\n🔗 **Conceptual Overlaps:**\n- This paper shares ${paper.entities.slice(0, 2).map((e: any) => e.text).join(', ')} with ${allPapers.length - 1} other papers in your collection\n- Similar claims about methodology improvements found in related studies\n\n**Cross-Paper Relationships:**\n- **Supports**: Findings align with previous work on AI applications\n- **Extends**: Builds upon established machine learning frameworks\n- **Contradicts**: Challenges traditional approaches mentioned in earlier papers`,
        type: 'connection',
        citations: allPapers.map(p => p.id),
        confidence: 0.85
      }
    }
    
    // Default response
    return {
      id: `msg_${Date.now()}`,
      role: 'assistant',
      content: `Based on "${paper.title}", I can help you analyze its ${paper.claims.length} claims and ${paper.entities.length} entities. The paper focuses on ${paper.entities.slice(0, 3).map((e: any) => e.text).join(', ')}.\n\n**Ask me about:**\n- Summarizing key findings\n- Critiquing methodology\n- Finding connections to other papers\n- Explaining specific claims or concepts`,
      type: 'question',
      citations: [paper.id],
      confidence: 0.90
    }
  }

  const quickActions = [
    {
      label: 'Summarize',
      icon: FileText,
      action: () => setInput('Summarize the key findings of this paper')
    },
    {
      label: 'Critique',
      icon: AlertTriangle,
      action: () => setInput('What are the limitations and weaknesses of this study?')
    },
    {
      label: 'Connect',
      icon: Link2,
      action: () => setInput('How does this paper connect to other related work?')
    },
    {
      label: 'Insights',
      icon: Lightbulb,
      action: () => setInput('What are the most important insights from this research?')
    }
  ]

  const getMessageIcon = (type?: string) => {
    switch (type) {
      case 'summary': return <FileText className="w-4 h-4 text-blue-500" />
      case 'critique': return <AlertTriangle className="w-4 h-4 text-orange-500" />
      case 'connection': return <Link2 className="w-4 h-4 text-green-500" />
      case 'question': return <Search className="w-4 h-4 text-purple-500" />
      default: return <Brain className="w-4 h-4 text-gray-500" />
    }
  }

  if (!selectedPaper) {
    return (
      <div className="h-full flex items-center justify-center p-8">
        <div className="text-center">
          <Brain className="w-12 h-12 mx-auto text-gray-300 mb-4" />
          <h3 className="font-medium text-gray-900 mb-2">No Paper Selected</h3>
          <p className="text-sm text-gray-600">
            Upload and select a paper to start scientific analysis
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="border-b p-4 bg-white">
        <h3 className="font-medium text-gray-900 mb-1">
          Scientific Analysis
        </h3>
        <p className="text-sm text-gray-600 truncate">
          {selectedPaper.title}
        </p>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="space-y-4">
            <Card className="p-4">
              <div className="flex items-start gap-3">
                <Brain className="w-5 h-5 text-blue-500 mt-0.5" />
                <div>
                  <p className="text-sm">
                    I'm your scientific research assistant. I can help you analyze "{selectedPaper.title}" 
                    by examining its {selectedPaper.claims.length} claims and {selectedPaper.entities.length} entities.
                  </p>
                </div>
              </div>
            </Card>
            
            <div className="grid grid-cols-2 gap-2">
              {quickActions.map((action, index) => (
                <Button
                  key={index}
                  variant="outline"
                  size="sm"
                  onClick={action.action}
                  className="flex items-center gap-2 text-left justify-start h-auto p-3"
                >
                  <action.icon className="w-4 h-4" />
                  <span className="text-xs">{action.label}</span>
                </Button>
              ))}
            </div>
          </div>
        )}

        {messages.map(message => (
          <div key={message.id} className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            {message.role === 'assistant' ? (
              <Card className="max-w-[85%] p-4">
                <div className="flex items-start gap-3">
                  {getMessageIcon(message.type)}
                  <div className="flex-1">
                    <div className="prose prose-sm max-w-none">
                      <div dangerouslySetInnerHTML={{ 
                        __html: message.content.replace(/\n/g, '<br/>').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                      }} />
                    </div>
                    
                    {message.confidence && (
                      <div className="mt-2 flex items-center gap-2">
                        <Badge variant="secondary" className="text-xs">
                          Confidence: {Math.round(message.confidence * 100)}%
                        </Badge>
                        {message.citations && (
                          <Badge variant="outline" className="text-xs">
                            {message.citations.length} source{message.citations.length !== 1 ? 's' : ''}
                          </Badge>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </Card>
            ) : (
              <div className="max-w-[85%] bg-blue-500 text-white p-3 rounded-lg">
                {message.content}
              </div>
            )}
          </div>
        ))}
        
        {isLoading && (
          <div className="flex justify-start">
            <Card className="p-4">
              <div className="flex items-center gap-3">
                <Brain className="w-5 h-5 text-blue-500 animate-pulse" />
                <div className="text-sm text-gray-600">
                  Analyzing scientific content...
                </div>
              </div>
            </Card>
          </div>
        )}
      </div>

      {/* Input */}
      <div className="border-t p-4 bg-white">
        <div className="flex gap-2">
          <Input
            placeholder="Ask about claims, critique methodology, find connections..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSend()}
            disabled={isLoading}
          />
          <Button onClick={handleSend} disabled={!input.trim() || isLoading}>
            <Send className="w-4 h-4" />
          </Button>
        </div>
      </div>
    </div>
  )
}

export default ScientificChat