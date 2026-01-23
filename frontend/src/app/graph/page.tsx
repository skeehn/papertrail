"use client"

import React, { useState } from 'react'
import { AppLayout, PageHeader, PageContent } from '@/components/layout/app-layout'
import { Button } from '@/components/ui/button'
import { Network, Maximize, Download } from 'lucide-react'
import GraphVisualization from '@/components/graph/graph-visualization'

export default function GraphPage() {
  const [isFullscreen, setIsFullscreen] = useState(false)

  const handleExport = () => {
    // The export functionality is handled within GraphVisualization component
    // Trigger it via the button in the component
    const exportButton = document.querySelector('[data-export-graph]') as HTMLButtonElement
    if (exportButton) {
      exportButton.click()
    }
  }

  const handleFullscreen = () => {
    if (!isFullscreen) {
      // Request fullscreen
      const element = document.documentElement
      if (element.requestFullscreen) {
        element.requestFullscreen().then(() => setIsFullscreen(true))
      }
    } else {
      // Exit fullscreen
      if (document.exitFullscreen) {
        document.exitFullscreen().then(() => setIsFullscreen(false))
      }
    }
  }

  // Listen for fullscreen changes
  React.useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement)
    }
    document.addEventListener('fullscreenchange', handleFullscreenChange)
    return () => document.removeEventListener('fullscreenchange', handleFullscreenChange)
  }, [])

  return (
    <AppLayout>
      <PageHeader
        title="Knowledge Graph"
        description="Explore relationships between papers, claims, and concepts"
        actions={
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={handleExport}>
              <Download className="w-4 h-4 mr-2" />
              Export
            </Button>
            <Button variant="outline" size="sm" onClick={handleFullscreen}>
              <Maximize className="w-4 h-4 mr-2" />
              {isFullscreen ? 'Exit Fullscreen' : 'Fullscreen'}
            </Button>
          </div>
        }
      />
      <PageContent maxWidth="full">
        <div className="h-[calc(100vh-200px)] min-h-[600px] w-full rounded-lg border bg-card overflow-hidden shadow-sm">
          <GraphVisualization className="h-full" />
        </div>
      </PageContent>
    </AppLayout>
  )
}
