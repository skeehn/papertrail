"use client"

import React from 'react'
import { AppLayout, PageHeader, PageContent } from '@/components/layout/app-layout'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Network, Maximize, Download } from 'lucide-react'

export default function GraphPage() {
  return (
    <AppLayout>
      <PageHeader
        title="Knowledge Graph"
        description="Explore relationships between papers, claims, and concepts"
        actions={
          <div className="flex gap-2">
            <Button variant="outline" size="sm">
              <Download className="w-4 h-4 mr-2" />
              Export
            </Button>
            <Button variant="outline" size="sm">
              <Maximize className="w-4 h-4 mr-2" />
              Fullscreen
            </Button>
          </div>
        }
      />
      <PageContent maxWidth="full">
        <Card className="p-12 text-center min-h-[600px] flex items-center justify-center">
          <div className="max-w-md">
            <div className="w-16 h-16 bg-gradient-to-br from-purple-500/10 to-purple-600/10 rounded-full flex items-center justify-center mx-auto mb-4">
              <Network className="w-8 h-8 text-purple-600" />
            </div>
            <h3 className="text-xl font-semibold mb-2">Graph Visualization</h3>
            <p className="text-muted-foreground mb-6">
              Your knowledge graph will appear here as you add papers and extract claims
            </p>
            <p className="text-sm text-muted-foreground">
              Upload papers to start building your research knowledge graph
            </p>
          </div>
        </Card>
      </PageContent>
    </AppLayout>
  )
}
