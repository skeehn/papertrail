"use client"

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react'
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
  Plus,
  Pin,
  PinOff,
  Trash2,
  Check,
  X,
  type LucideIcon,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import {
  conversationStore,
  type StoredConversationMeta,
} from '@/lib/conversations'

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
}

const navItems: NavItem[] = [
  { title: 'Dashboard', href: '/dashboard', icon: Home },
  { title: 'Chat', href: '/', icon: MessageSquare },
  { title: 'Papers', href: '/papers', icon: FileText },
  { title: 'Graph', href: '/graph', icon: Network },
  { title: 'Audit Trail', href: '/audit', icon: ClipboardList },
  { title: 'Settings', href: '/settings', icon: Settings },
]

/** Live chat-controller API registered by EnhancedChat on window. */
interface ChatController {
  conversations: StoredConversationMeta[]
  activeId: string | null
  startNewChat: () => void
  switchTo: (id: string) => void
  deleteConversation: (id: string) => void
  renameConversation: (id: string, title: string) => void
  togglePinConversation: (id: string) => void
}

function getController(): ChatController | null {
  return (typeof window !== 'undefined' ? (window as any).__papertrailChat : null) ?? null
}

export function AppSidebar() {
  const { isCollapsed, setIsCollapsed } = useSidebar()
  const pathname = usePathname()

  const [conversations, setConversations] = useState<StoredConversationMeta[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editTitle, setEditTitle] = useState('')

  const syncFromController = useCallback(() => {
    const ctrl = getController()
    if (ctrl) {
      setConversations(ctrl.conversations)
      setActiveId(ctrl.activeId)
    } else {
      setConversations(conversationStore.list())
    }
  }, [])

  useEffect(() => {
    syncFromController()
    const unsub = conversationStore.subscribe(syncFromController)
    const onRegistry = () => syncFromController()
    const onStorage = (e: StorageEvent) => {
      if (!e.key || e.key === 'papertrail_conversations_index') syncFromController()
    }
    window.addEventListener('papertrail:chat-registry', onRegistry)
    window.addEventListener('storage', onStorage)
    return () => {
      unsub()
      window.removeEventListener('papertrail:chat-registry', onRegistry)
      window.removeEventListener('storage', onStorage)
    }
  }, [syncFromController])

  const handleNewChat = () => {
    const ctrl = getController()
    if (ctrl) ctrl.startNewChat()
    if (pathname !== '/') window.location.href = '/'
  }

  const handleSelect = (id: string) => {
    if (pathname !== '/') {
      // Store the target so the chat picks it up after navigation.
      try { sessionStorage.setItem('papertrail_open_conversation', id) } catch {}
      window.location.href = '/'
      return
    }
    getController()?.switchTo(id)
  }

  const handleDelete = (id: string) => {
    const ctrl = getController()
    if (ctrl) ctrl.deleteConversation(id)
    else conversationStore.remove(id)
  }

  const handleRename = (id: string, title: string) => {
    const ctrl = getController()
    if (ctrl) ctrl.renameConversation(id, title)
    else conversationStore.rename(id, title)
  }

  const handleTogglePin = (id: string) => {
    const ctrl = getController()
    if (ctrl) ctrl.togglePinConversation(id)
    else conversationStore.togglePinned(id)
  }

  const startEdit = (conv: StoredConversationMeta) => {
    setEditingId(conv.id)
    setEditTitle(conv.title)
  }

  const saveEdit = (id: string) => {
    if (editTitle.trim()) handleRename(id, editTitle.trim())
    setEditingId(null)
  }

  /* Group: pinned first, then Today / Yesterday / This week / Older. */
  const now = new Date()
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime()
  const startOfYesterday = startOfToday - 86_400_000
  const weekAgo = startOfToday - 7 * 86_400_000

  const pinned = conversations.filter((c) => c.pinned)
  const rest = conversations.filter((c) => !c.pinned)
  const groups: Array<{ label: string; items: StoredConversationMeta[] }> = [
    { label: 'Today', items: rest.filter((c) => c.updatedAt >= startOfToday) },
    { label: 'Yesterday', items: rest.filter((c) => c.updatedAt >= startOfYesterday && c.updatedAt < startOfToday) },
    { label: 'Last 7 days', items: rest.filter((c) => c.updatedAt >= weekAgo && c.updatedAt < startOfYesterday) },
    { label: 'Older', items: rest.filter((c) => c.updatedAt < weekAgo) },
  ].filter((g) => g.items.length > 0)

  const ConversationRow = ({ conv }: { conv: StoredConversationMeta }) => {
    const isActive = conv.id === activeId
    const isEditing = editingId === conv.id

    return (
      <div
        className={cn(
          'group relative rounded-lg px-3 py-2 cursor-pointer transition-colors',
          'hover:bg-muted/50',
          isActive && 'bg-primary/10 text-foreground'
        )}
        onClick={() => !isEditing && handleSelect(conv.id)}
      >
        {isEditing ? (
          <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
            <input
              value={editTitle}
              onChange={(e) => setEditTitle(e.target.value)}
              onBlur={() => saveEdit(conv.id)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') saveEdit(conv.id)
                if (e.key === 'Escape') setEditingId(null)
              }}
              autoFocus
              className="h-6 w-full rounded bg-background px-2 text-xs text-foreground outline-none ring-1 ring-primary/40"
            />
            <button onClick={() => saveEdit(conv.id)} className="text-muted-foreground hover:text-foreground">
              <Check className="h-3.5 w-3.5" />
            </button>
            <button onClick={() => setEditingId(null)} className="text-muted-foreground hover:text-foreground">
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        ) : (
          <div className="flex items-start gap-2">
            <div className="min-w-0 flex-1">
              <div className="truncate text-sm">
                {conv.title || 'New chat'}
              </div>
              <div className="mt-0.5 flex items-center gap-1.5 text-[10px] text-muted-foreground">
                {conv.pinned && <Pin className="h-2.5 w-2.5" />}
                <span>{new Date(conv.updatedAt).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}</span>
                <span>·</span>
                <span>{conv.messageCount} msgs</span>
              </div>
            </div>
            <div className="absolute right-1.5 top-1.5 hidden items-center gap-0.5 group-hover:flex">
              <button
                onClick={(e) => { e.stopPropagation(); handleTogglePin(conv.id) }}
                title={conv.pinned ? 'Unpin' : 'Pin'}
                className="rounded p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
              >
                {conv.pinned ? <PinOff className="h-3 w-3" /> : <Pin className="h-3 w-3" />}
              </button>
              <button
                onClick={(e) => { e.stopPropagation(); startEdit(conv) }}
                className="rounded p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
                title="Rename"
              >
                <Settings className="h-3 w-3 rotate-90" />
              </button>
              <button
                onClick={(e) => { e.stopPropagation(); handleDelete(conv.id) }}
                className="rounded p-1 text-muted-foreground hover:bg-muted hover:text-destructive"
                title="Delete"
              >
                <Trash2 className="h-3 w-3" />
              </button>
            </div>
          </div>
        )}
      </div>
    )
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
              <div className="w-8 h-8 bg-primary text-primary-foreground rounded-lg flex items-center justify-center font-bold text-sm shadow-sm shadow-primary/30">
                PT
              </div>
              <div className="flex-1 min-w-0">
                <h2 className="font-semibold text-sm">PaperTrail</h2>
                <p className="text-xs text-muted-foreground">Research Assistant</p>
              </div>
            </div>
          )}
          {isCollapsed && (
            <div className="w-8 h-8 bg-primary text-primary-foreground rounded-lg flex items-center justify-center font-bold text-sm shadow-sm shadow-primary/30">
              PT
            </div>
          )}
          <Button
            onClick={() => setIsCollapsed(!isCollapsed)}
            variant="ghost"
            size="icon"
            className="h-8 w-8 text-muted-foreground hover:text-foreground"
          >
            {isCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
          </Button>
        </div>

        {/* New chat + Navigation */}
        <div className="px-2 pt-1">
          <button
            onClick={handleNewChat}
            className={cn(
              'flex w-full items-center gap-2 rounded-lg bg-primary/12 px-3 py-2 text-sm font-medium text-primary transition-colors hover:bg-primary/20',
              isCollapsed && 'justify-center px-2'
            )}
          >
            <Plus className="w-4 h-4 shrink-0" />
            {!isCollapsed && <span>New chat</span>}
          </button>
        </div>

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
                  'flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors',
                  'hover:bg-muted/50',
                  isActive && 'bg-primary/12 text-primary font-medium',
                  !isActive && 'text-muted-foreground',
                  isCollapsed && 'justify-center px-2'
                )}
              >
                <Icon className={cn('w-4 h-4 flex-shrink-0')} />
                {!isCollapsed && <span className="flex-1">{item.title}</span>}
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

        {/* Conversations list */}
        {!isCollapsed && (
          <div className="flex-1 overflow-y-auto px-2 py-2 border-t border-border/50 mt-1 thin-scroll">
            <div className="px-3 py-2 text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Conversations
            </div>
            <div className="space-y-1 pb-4">
              {pinned.map((conv) => <ConversationRow key={conv.id} conv={conv} />)}
              {groups.map((group) => (
                <div key={group.label}>
                  <div className="px-3 pt-2 pb-1 text-[10px] font-medium uppercase tracking-wider text-muted-foreground/70">
                    {group.label}
                  </div>
                  {group.items.map((conv) => <ConversationRow key={conv.id} conv={conv} />)}
                </div>
              ))}
              {conversations.length === 0 && (
                <p className="px-3 py-6 text-center text-xs text-muted-foreground">
                  No conversations yet.
                  <br />
                  Start chatting to see history here.
                </p>
              )}
            </div>
          </div>
        )}
      </aside>
    </TooltipProvider>
  )
}
