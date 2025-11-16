"use client"

import React from 'react'
import { AppLayout, PageHeader, PageContent } from '@/components/layout/app-layout'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { ClipboardList, Download, Filter } from 'lucide-react'
import { Input } from '@/components/ui/input'

export default function AuditPage() {
  return (
    <AppLayout>
      <PageHeader
        title="Audit Trail"
        description="Comprehensive log of all system activities and AI interactions"
        actions={
          <Button variant="outline">
            <Download className="w-4 h-4 mr-2" />
            Export
          </Button>
        }
      />
      <PageContent>
        <div className="space-y-6">
          {/* Search and Filters */}
          <div className="flex gap-4">
            <div className="flex-1">
              <Input
                placeholder="Search audit log..."
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
                <ClipboardList className="w-8 h-8 text-muted-foreground" />
              </div>
              <h3 className="text-xl font-semibold mb-2">No audit entries yet</h3>
              <p className="text-muted-foreground">
                All system activities and interactions will be logged here for compliance and review
              </p>
            </div>
          </Card>
        </div>
      </PageContent>
    </AppLayout>
  )
}
