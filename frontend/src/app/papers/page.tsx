"use client"

import React from 'react'
import { AppLayout, PageHeader, PageContent } from '@/components/layout/app-layout'
import { Button } from '@/components/ui/button'
import { Upload } from 'lucide-react'
import PapersLibraryContent from './papers-library'

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
        <PapersLibraryContent />
      </PageContent>
    </AppLayout>
  )
}
