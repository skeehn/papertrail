"use client"

import React from 'react'
import { AppLayout, PageHeader, PageContent } from '@/components/layout/app-layout'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Upload, FileText, Search, Filter } from 'lucide-react'
import { Input } from '@/components/ui/input'

export default function PapersPage() {
  return (
    <AppLayout>
      <PageHeader
        title="Papers Library"
        description="Manage and organize your research papers"
        actions={
          <Button>
            <Upload className="w-4 h-4 mr-2" />
            Upload Paper
          </Button>
        }
      />
      <PageContent>
        <div className="space-y-6">
          {/* Search and Filters */}
          <div className="flex gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                placeholder="Search papers..."
                className="pl-10"
              />
            </div>
            <Button variant="outline">
              <Filter className="w-4 h-4 mr-2" />
              Filters
            </Button>
          </div>

          {/* Empty State */}
          <Card className="p-12 text-center">
            <div className="max-w-md mx-auto">
              <div className="w-16 h-16 bg-muted rounded-full flex items-center justify-center mx-auto mb-4">
                <FileText className="w-8 h-8 text-muted-foreground" />
              </div>
              <h3 className="text-xl font-semibold mb-2">No papers yet</h3>
              <p className="text-muted-foreground mb-6">
                Upload your first research paper to get started with PaperTrail
              </p>
              <Button>
                <Upload className="w-4 h-4 mr-2" />
                Upload Your First Paper
              </Button>
            </div>
          </Card>
        </div>
      </PageContent>
    </AppLayout>
  )
}
