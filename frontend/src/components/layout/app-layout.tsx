"use client"

import React from 'react'
import { AppSidebar, SidebarProvider } from './app-sidebar'
import { cn } from '@/lib/utils'

interface AppLayoutProps {
  children: React.ReactNode
  className?: string
}

export function AppLayout({ children, className }: AppLayoutProps) {
  return (
    <SidebarProvider defaultCollapsed={false}>
      <div className="flex min-h-screen bg-background">
        <AppSidebar />
        <main className={cn('flex-1 flex flex-col overflow-hidden', className)}>
          {children}
        </main>
      </div>
    </SidebarProvider>
  )
}

interface PageHeaderProps {
  title: string
  description?: string
  actions?: React.ReactNode
}

export function PageHeader({ title, description, actions }: PageHeaderProps) {
  return (
    <div className="border-b bg-card/50 backdrop-blur-sm sticky top-0 z-10">
      <div className="px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
            {description && (
              <p className="text-sm text-muted-foreground mt-1">{description}</p>
            )}
          </div>
          {actions && <div className="flex items-center gap-2">{actions}</div>}
        </div>
      </div>
    </div>
  )
}

interface PageContentProps {
  children: React.ReactNode
  className?: string
  maxWidth?: 'sm' | 'md' | 'lg' | 'xl' | '2xl' | '4xl' | '6xl' | 'full'
}

export function PageContent({ children, className, maxWidth = '6xl' }: PageContentProps) {
  const maxWidthClass = {
    sm: 'max-w-sm',
    md: 'max-w-md',
    lg: 'max-w-lg',
    xl: 'max-w-xl',
    '2xl': 'max-w-2xl',
    '4xl': 'max-w-4xl',
    '6xl': 'max-w-6xl',
    full: 'max-w-full',
  }[maxWidth]

  return (
    <div className="flex-1 overflow-y-auto">
      <div className={cn('mx-auto p-6', maxWidthClass, className)}>
        {children}
      </div>
    </div>
  )
}
