"use client"

import React from "react"
import { AppLayout } from '@/components/layout/app-layout'
import EnhancedChat from '@/components/chat/enhanced-chat'

export default function Home() {
  return (
    <AppLayout>
      <EnhancedChat />
    </AppLayout>
  )
}
