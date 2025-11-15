"use client"

import React from 'react'
import { AppLayout, PageHeader, PageContent } from '@/components/layout/app-layout'
import SettingsContent from './settings-content'

export default function SettingsPage() {
  return (
    <AppLayout>
      <PageHeader
        title="Settings"
        description="Manage your preferences and account settings"
      />
      <PageContent maxWidth="4xl">
        <SettingsContent />
      </PageContent>
    </AppLayout>
  )
}
