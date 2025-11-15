"use client"

import React, { createContext, useContext, useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  Home,
  MessageSquare,
  FileText,
  Network,
  ClipboardList,
  Settings,
  ChevronLeft,
  ChevronRight,
  type LucideIcon
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'

interface SidebarContextType {
  isCollapsed: boolean
  setIsCollapsed: (collapsed: boolean) => void
}

const SidebarContext = createContext<SidebarContextType | undefined>(undefined)

export function useSidebar() {
  const context = useContext(SidebarContext)
  if (!context) {
    throw new Error('useSidebar must be used within a SidebarProvider')
  }
  return context
}

interface SidebarProviderProps {
  children: React.ReactNode
  defaultCollapsed?: boolean
}

export function SidebarProvider({ children, defaultCollapsed = false }: SidebarProviderProps) {
  const [isCollapsed, setIsCollapsed] = useState(defaultCollapsed)

  return (
    <SidebarContext.Provider value={{ isCollapsed, setIsCollapsed }}>
      {children}
    </SidebarContext.Provider>
  )
}

interface NavItem {
  title: string
  href: string
  icon: LucideIcon
  badge?: string
}

const navItems: NavItem[] = [
  {
    title: 'Dashboard',
    href: '/dashboard',
    icon: Home,
  },
  {
    title: 'Chat',
    href: '/',
    icon: MessageSquare,
  },
  {
    title: 'Papers',
    href: '/papers',
    icon: FileText,
  },
  {
    title: 'Graph',
    href: '/graph',
    icon: Network,
  },
  {
    title: 'Audit Trail',
    href: '/audit',
    icon: ClipboardList,
  },
  {
    title: 'Settings',
    href: '/settings',
    icon: Settings,
  },
]

export function AppSidebar() {
  const { isCollapsed, setIsCollapsed } = useSidebar()
  const pathname = usePathname()

  return (
    <TooltipProvider delayDuration={0}>
      <aside
        className={cn(
          'sticky top-0 h-screen border-r bg-sidebar text-sidebar-foreground transition-all duration-300 ease-in-out flex flex-col',
          isCollapsed ? 'w-[60px]' : 'w-[280px]'
        )}
      >
        {/* Header */}
        <div className={cn(
          'flex items-center justify-between px-4 py-5 border-b border-sidebar-border',
          isCollapsed && 'justify-center px-2'
        )}>
          {!isCollapsed && (
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 bg-gradient-to-br from-primary-500 to-primary-700 rounded-lg flex items-center justify-center text-white font-bold text-sm">
                PT
              </div>
              <div>
                <h2 className="font-semibold text-sm">PaperTrail</h2>
                <p className="text-xs text-sidebar-foreground/60">Research Assistant</p>
              </div>
            </div>
          )}
          {isCollapsed && (
            <div className="w-8 h-8 bg-gradient-to-br from-primary-500 to-primary-700 rounded-lg flex items-center justify-center text-white font-bold text-sm">
              PT
            </div>
          )}
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-2 py-4 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            const Icon = item.icon
            const isActive = pathname === item.href ||
                           (item.href !== '/' && pathname?.startsWith(item.href))

            const navItem = (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200',
                  'hover:bg-sidebar-accent hover:text-sidebar-accent-foreground',
                  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sidebar-ring',
                  isActive && 'bg-sidebar-accent text-sidebar-accent-foreground',
                  isCollapsed && 'justify-center px-2'
                )}
              >
                <Icon className={cn('w-5 h-5 flex-shrink-0', isActive && 'text-sidebar-primary')} />
                {!isCollapsed && (
                  <>
                    <span className="flex-1">{item.title}</span>
                    {item.badge && (
                      <span className="px-2 py-0.5 text-xs bg-sidebar-primary text-sidebar-primary-foreground rounded-full">
                        {item.badge}
                      </span>
                    )}
                  </>
                )}
              </Link>
            )

            if (isCollapsed) {
              return (
                <Tooltip key={item.href}>
                  <TooltipTrigger asChild>
                    {navItem}
                  </TooltipTrigger>
                  <TooltipContent side="right" className="flex items-center gap-2">
                    {item.title}
                    {item.badge && (
                      <span className="ml-auto text-xs">{item.badge}</span>
                    )}
                  </TooltipContent>
                </Tooltip>
              )
            }

            return navItem
          })}
        </nav>

        {/* Footer - Toggle Button */}
        <div className={cn(
          'p-2 border-t border-sidebar-border',
          isCollapsed && 'flex justify-center'
        )}>
          <Button
            onClick={() => setIsCollapsed(!isCollapsed)}
            variant="ghost"
            size="sm"
            className="w-full justify-start gap-2 text-sidebar-foreground/60 hover:text-sidebar-foreground hover:bg-sidebar-accent"
          >
            {isCollapsed ? (
              <ChevronRight className="w-4 h-4" />
            ) : (
              <>
                <ChevronLeft className="w-4 h-4" />
                <span className="text-xs">Collapse</span>
              </>
            )}
          </Button>
        </div>
      </aside>
    </TooltipProvider>
  )
}
