"use client"

import React, { createContext, useContext, useState, useEffect } from 'react'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import {
  Home,
  MessageSquare,
  FileText,
  Network,
  ClipboardList,
  Settings,
  ChevronLeft,
  ChevronRight,
  Clock,
  type LucideIcon
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { useConversationPersistence } from '@/hooks/use-memory-persistence'

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

interface Conversation {
  id: string
  title: string
  timestamp: number
  messageCount: number
}

export function AppSidebar() {
  const { isCollapsed, setIsCollapsed } = useSidebar()
  const pathname = usePathname()
  const router = useRouter()
  const { loadConversation } = useConversationPersistence()
  const [conversations, setConversations] = useState<Conversation[]>([])

  // Load conversation history from localStorage
  useEffect(() => {
    const loadConversationHistory = () => {
      try {
        if (typeof window === 'undefined') return
        
        // Get current conversation
        const currentMessages = loadConversation()
        const currentConvId = localStorage.getItem('papertrail_conversation_id')
        
        // Get all conversation IDs from localStorage
        const allKeys = Object.keys(localStorage)
        const conversationKeys = allKeys.filter(key => key.startsWith('papertrail_conversation_'))
        
        const convs: Conversation[] = []
        
        // Add current conversation if it exists
        if (currentMessages.length > 0 && currentConvId) {
          const firstMessage = currentMessages[0] as any
          const lastMessage = currentMessages[currentMessages.length - 1] as any
          // Extract content from parts (AI SDK v5) or legacy content field
          const messageContent = typeof firstMessage.content === 'string'
            ? firstMessage.content
            : firstMessage.parts?.filter((p: any) => p.type === 'text').map((p: any) => p.text).join('') || ''
          const title = messageContent
            ? messageContent.slice(0, 50)
            : 'New Conversation'
          
          convs.push({
            id: currentConvId,
            title: title || 'New Conversation',
            timestamp: lastMessage.timestamp || lastMessage.createdAt || Date.now(),
            messageCount: currentMessages.length
          })
        }
        
        // Sort by timestamp (newest first) and limit to 15
        convs.sort((a, b) => b.timestamp - a.timestamp)
        setConversations(convs.slice(0, 15))
      } catch (error) {
        console.error('Error loading conversation history:', error)
      }
    }
    
    loadConversationHistory()
    // Refresh every 5 seconds to catch new conversations
    const interval = setInterval(loadConversationHistory, 5000)
    return () => clearInterval(interval)
  }, [loadConversation])

  const handleConversationClick = (convId: string) => {
    // Navigate to chat and load conversation
    router.push('/')
    // The chat component will load the conversation on mount
  }

  return (
    <TooltipProvider delayDuration={0}>
      <aside
        className={cn(
          'sticky top-0 h-screen bg-sidebar text-sidebar-foreground transition-all duration-300 ease-in-out flex flex-col',
          isCollapsed ? 'w-[64px]' : 'w-[250px]',
          'border-r border-border/50'
        )}
      >
        {/* Header */}
        <div className={cn(
          'flex items-center justify-between px-4 py-4',
          isCollapsed && 'justify-center px-2'
        )}>
          {!isCollapsed && (
            <div className="flex items-center gap-3 flex-1">
              <div className="w-8 h-8 bg-foreground text-background rounded flex items-center justify-center font-bold text-sm">
                PT
              </div>
              <div className="flex-1 min-w-0">
                <h2 className="font-semibold text-sm">PaperTrail</h2>
                <p className="text-xs text-muted-foreground">Research Assistant</p>
              </div>
            </div>
          )}
          {isCollapsed && (
            <div className="w-8 h-8 bg-foreground text-background rounded flex items-center justify-center font-bold text-sm">
              PT
            </div>
          )}
          {/* Toggle Button in Header */}
          <Button
            onClick={() => setIsCollapsed(!isCollapsed)}
            variant="ghost"
            size="icon"
            className="h-8 w-8 text-muted-foreground hover:text-foreground"
          >
            {isCollapsed ? (
              <ChevronRight className="w-4 h-4" />
            ) : (
              <ChevronLeft className="w-4 h-4" />
            )}
          </Button>
        </div>

        {/* Navigation */}
        <nav className="px-2 py-2 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon
            const isActive = pathname === item.href ||
                           (item.href !== '/' && pathname?.startsWith(item.href))

            const navItem = (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  'flex items-center gap-3 px-3 py-2 rounded text-sm transition-colors',
                  'hover:bg-muted/50',
                  isActive && 'bg-muted text-foreground',
                  !isActive && 'text-muted-foreground',
                  isCollapsed && 'justify-center px-2'
                )}
              >
                <Icon className={cn('w-4 h-4 flex-shrink-0')} />
                {!isCollapsed && (
                  <span className="flex-1">{item.title}</span>
                )}
              </Link>
            )

            if (isCollapsed) {
              return (
                <Tooltip key={item.href}>
                  <TooltipTrigger asChild>
                    {navItem}
                  </TooltipTrigger>
                  <TooltipContent side="right">
                    {item.title}
                  </TooltipContent>
                </Tooltip>
              )
            }

            return navItem
          })}
        </nav>

        {/* Conversation History */}
        {!isCollapsed && conversations.length > 0 && (
          <div className="flex-1 overflow-y-auto px-2 py-2 border-t border-border/50 mt-2">
            <div className="px-3 py-2 text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Conversations
            </div>
            <div className="space-y-1">
              {conversations.map((conv) => (
                <button
                  key={conv.id}
                  onClick={() => handleConversationClick(conv.id)}
                  className={cn(
                    'w-full text-left px-3 py-2 rounded text-sm transition-colors',
                    'hover:bg-muted/50 text-muted-foreground hover:text-foreground',
                    'flex items-start gap-2'
                  )}
                >
                  <Clock className="w-3 h-3 mt-0.5 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div className="truncate">{conv.title}</div>
                    <div className="text-xs text-muted-foreground mt-0.5">
                      {new Date(conv.timestamp).toLocaleDateString()}
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}

      </aside>
    </TooltipProvider>
  )
}
