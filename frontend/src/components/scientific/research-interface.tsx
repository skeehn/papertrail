"use client"

import React, { useState } from 'react'
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from '@/components/ui/resizable'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Network,
  MessageCircle,
  Brain,
  Upload,
  Lightbulb,
} from 'lucide-react'

import PaperUpload from './paper-upload'
import ScientificChat from './scientific-chat'
import ArgumentGraph from './argument-graph'
import ClaimsList from './claims-list'
import IntelligentChat from './intelligent-chat'

interface ResearchInterfaceProps {
  className?: string
}

interface PaperData {
  id: string
  title: string
  authors: string[]
  abstract: string
  claims: any[]
  entities: any[]
  metadata: any
}

const ResearchInterface = ({ className }: ResearchInterfaceProps) => {
  const [papers, setPapers] = useState<PaperData[]>([])
  const [selectedPaper, setSelectedPaper] = useState<string | null>(null)
  const [activeView, setActiveView] = useState<'chat' | 'upload' | 'analysis'>('chat')

  const handlePaperUploaded = (paperId: string, metadata: any) => {
    const newPaper: PaperData = {
      id: paperId,
      title: metadata.title,
      authors: metadata.authors || [],
      abstract: metadata.abstract || '',
      claims: metadata.claims || [],
      entities: metadata.entities || [],
      metadata
    }
    
    setPapers(prev => [...prev, newPaper])
    setSelectedPaper(paperId)
    setActiveView('analysis')
  }

  const selectedPaperData = papers.find(p => p.id === selectedPaper)

  return (
    <div className={`h-screen bg-gray-50 ${className}`}>
      {/* Header */}
      <div className="border-b bg-white px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              PaperTrail 2.0
            </h1>
            <p className="text-sm text-gray-600">
              Reliable argument maps for science
            </p>
          </div>
          
          <div className="flex items-center gap-2">
            <Button
              variant={activeView === 'chat' ? 'default' : 'outline'}
              onClick={() => setActiveView('chat')}
              className="flex items-center gap-2"
            >
              <MessageCircle className="w-4 h-4" />
              Chat
            </Button>
            <Button
              variant={activeView === 'upload' ? 'default' : 'outline'}
              onClick={() => setActiveView('upload')}
              className="flex items-center gap-2"
            >
              <Upload className="w-4 h-4" />
              Upload Papers
            </Button>
            <Button
              variant={activeView === 'analysis' ? 'default' : 'outline'}
              onClick={() => setActiveView('analysis')}
              className="flex items-center gap-2"
            >
              <Network className="w-4 h-4" />
              Analysis
            </Button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-hidden">
        {activeView === 'chat' ? (
          <div className="h-full">
            <IntelligentChat papers={papers} />
          </div>
        ) : activeView === 'upload' ? (
          <div className="p-6 max-w-4xl mx-auto">
            <PaperUpload onPaperUploaded={handlePaperUploaded} />
            
            {/* Recent Papers */}
            {papers.length > 0 && (
              <Card className="mt-6 p-6">
                <h3 className="font-semibold mb-4">Recent Papers</h3>
                <div className="space-y-3">
                  {papers.map(paper => (
                    <div 
                      key={paper.id}
                      className="flex items-center justify-between p-3 border rounded-lg hover:bg-gray-50 cursor-pointer"
                      onClick={() => {
                        setSelectedPaper(paper.id)
                        setActiveView('analysis')
                      }}
                    >
                      <div>
                        <h4 className="font-medium">{paper.title}</h4>
                        <p className="text-sm text-gray-600">
                          by {paper.authors.join(', ')}
                        </p>
                        <p className="text-xs text-gray-500">
                          {paper.claims.length} claims • {paper.entities.length} entities
                        </p>
                      </div>
                      <Button variant="outline" size="sm">
                        Analyze
                      </Button>
                    </div>
                  ))}
                </div>
              </Card>
            )}
          </div>
        ) : (
          /* Analysis View - Split Pane Interface */
          <ResizablePanelGroup direction="horizontal" className="h-full">
            {/* Left Panel - Scientific Chat */}
            <ResizablePanel defaultSize={40} minSize={30}>
              <div className="h-full flex flex-col">
                {/* Paper Selector */}
                {papers.length > 1 && (
                  <div className="border-b bg-white p-4">
                    <label className="text-sm font-medium text-gray-700 mb-2 block">
                      Active Paper:
                    </label>
                    <select 
                      value={selectedPaper || ''}
                      onChange={(e) => setSelectedPaper(e.target.value)}
                      className="w-full p-2 border rounded-lg"
                    >
                      {papers.map(paper => (
                        <option key={paper.id} value={paper.id}>
                          {paper.title}
                        </option>
                      ))}
                    </select>
                  </div>
                )}
                
                {/* Scientific Chat Interface */}
                <div className="flex-1">
                  <ScientificChat 
                    papers={papers}
                    selectedPaper={selectedPaperData}
                  />
                </div>
              </div>
            </ResizablePanel>

            <ResizableHandle />

            {/* Right Panel - Visualizations */}
            <ResizablePanel defaultSize={60} minSize={40}>
              <div className="h-full bg-white">
                <Tabs defaultValue="graph" className="h-full flex flex-col">
                  <TabsList className="grid w-full grid-cols-3 border-b rounded-none bg-gray-50">
                    <TabsTrigger value="graph" className="flex items-center gap-2">
                      <Network className="w-4 h-4" />
                      Argument Graph
                    </TabsTrigger>
                    <TabsTrigger value="claims" className="flex items-center gap-2">
                      <Brain className="w-4 h-4" />
                      Claims
                    </TabsTrigger>
                    <TabsTrigger value="insights" className="flex items-center gap-2">
                      <Lightbulb className="w-4 h-4" />
                      Insights
                    </TabsTrigger>
                  </TabsList>
                  
                  <div className="flex-1 overflow-hidden">
                    <TabsContent value="graph" className="h-full m-0">
                      <ArgumentGraph 
                        papers={papers}
                        selectedPaper={selectedPaperData}
                      />
                    </TabsContent>
                    
                    <TabsContent value="claims" className="h-full m-0 p-4">
                      <ClaimsList 
                        papers={papers}
                        selectedPaper={selectedPaperData}
                      />
                    </TabsContent>
                    
                    <TabsContent value="insights" className="h-full m-0 p-4">
                      <div className="text-center text-gray-500">
                        <Lightbulb className="w-12 h-12 mx-auto mb-4 text-gray-300" />
                        <h3 className="font-medium mb-2">AI Insights Coming Soon</h3>
                        <p className="text-sm">
                          Advanced analysis and pattern detection across papers
                        </p>
                      </div>
                    </TabsContent>
                  </div>
                </Tabs>
              </div>
            </ResizablePanel>
          </ResizablePanelGroup>
        )}
      </div>
    </div>
  )
}

export default ResearchInterface