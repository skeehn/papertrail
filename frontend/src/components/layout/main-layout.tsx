"use client"

import React, { useState } from 'react'
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from '@/components/ui/resizable'
import { Button } from '@/components/ui/button'
import { Brain, MessageCircle, Network, ChevronLeft, ChevronRight } from 'lucide-react'
import { cn } from '../../lib/utils'
import GraphVisualization from '@/components/graph/graph-visualization'
import MemoryPanel from '@/components/graph/memory-panel'
import TemporalMemoryPanel from '@/components/graph/temporal-memory-panel'
import MemorySearchPanel from '@/components/graph/memory-search-panel'

interface MainLayoutProps {
  chatComponent: React.ReactNode
  className?: string
}

const MainLayout = ({ chatComponent, className }: MainLayoutProps) => {
  const [activeTab, setActiveTab] = useState<'chat' | 'graph' | 'memory'>('chat')
  const [isRightPanelCollapsed, setIsRightPanelCollapsed] = useState(false)

  return (
    <div className={cn("flex h-screen overflow-hidden", className)}>
      <ResizablePanelGroup direction="horizontal">
        {/* Main Content Area */}
        <ResizablePanel defaultSize={70} minSize={50}>
          <div className="flex flex-col h-full">
            {/* Tab Navigation */}
            <div className="flex items-center justify-between border-b px-4 py-2 bg-gray-50">
              <div className="flex items-center gap-1">
                <Button
                  variant={activeTab === 'chat' ? 'default' : 'ghost'}
                  size="sm"
                  onClick={() => setActiveTab('chat')}
                  className="flex items-center gap-2"
                >
                  <MessageCircle size={16} />
                  Chat
                </Button>
                <Button
                  variant={activeTab === 'graph' ? 'default' : 'ghost'}
                  size="sm"
                  onClick={() => setActiveTab('graph')}
                  className="flex items-center gap-2"
                >
                  <Network size={16} />
                  Graph
                </Button>
                <Button
                  variant={activeTab === 'memory' ? 'default' : 'ghost'}
                  size="sm"
                  onClick={() => setActiveTab('memory')}
                  className="flex items-center gap-2"
                >
                  <Brain size={16} />
                  Memory
                </Button>
              </div>
              
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setIsRightPanelCollapsed(!isRightPanelCollapsed)}
                className="flex items-center gap-2"
              >
                {isRightPanelCollapsed ? <ChevronLeft size={16} /> : <ChevronRight size={16} />}
                {isRightPanelCollapsed ? 'Show Panel' : 'Hide Panel'}
              </Button>
            </div>

            {/* Tab Content */}
            <div className="flex-1 overflow-hidden">
              {activeTab === 'chat' && (
                <div className="h-full">
                  {chatComponent}
                </div>
              )}
              
              {activeTab === 'graph' && (
                <div className="h-full">
                  <GraphVisualization />
                </div>
              )}
              
              {activeTab === 'memory' && (
                <div className="h-full p-4 overflow-y-auto">
                  <div className="max-w-4xl mx-auto grid grid-cols-1 lg:grid-cols-2 gap-6">
                    <div className="space-y-4">
                      <MemoryPanel />
                      <MemorySearchPanel />
                    </div>
                    <div>
                      <TemporalMemoryPanel />
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </ResizablePanel>

        {/* Right Panel */}
        {!isRightPanelCollapsed && (
          <>
            <ResizableHandle />
            <ResizablePanel defaultSize={30} minSize={25} maxSize={50}>
              <div className="flex flex-col h-full border-l bg-gray-50/50">
                <div className="border-b px-4 py-3">
                  <h2 className="font-semibold text-sm flex items-center gap-2">
                    <Brain className="text-blue-500" size={16} />
                    Knowledge Graph
                  </h2>
                </div>
                
                <div className="flex-1 overflow-y-auto p-4 space-y-4">
                  <MemoryPanel />
                  
                  <div className="border-t pt-4">
                    <TemporalMemoryPanel />
                  </div>
                </div>
              </div>
            </ResizablePanel>
          </>
        )}
      </ResizablePanelGroup>
    </div>
  )
}

export default MainLayout