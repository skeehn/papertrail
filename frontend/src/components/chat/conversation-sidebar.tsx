"use client"

import React, { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Search, Plus, MessageSquare, Trash2, Edit2, Pin } from 'lucide-react'
import { cn } from '@/lib/utils'

interface Conversation {
  id: string
  title: string
  lastMessage: string
  timestamp: Date
  isPinned?: boolean
}

interface ConversationSidebarProps {
  conversations: Conversation[]
  activeId?: string
  onSelect: (id: string) => void
  onNew: () => void
  onDelete: (id: string) => void
  onRename: (id: string, newTitle: string) => void
  className?: string
}

export function ConversationSidebar({
  conversations,
  activeId,
  onSelect,
  onNew,
  onDelete,
  onRename,
  className
}: ConversationSidebarProps) {
  const [searchQuery, setSearchQuery] = useState('')
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editTitle, setEditTitle] = useState('')

  const filteredConversations = conversations.filter(conv =>
    conv.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    conv.lastMessage.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const groupedConversations = {
    today: [] as Conversation[],
    yesterday: [] as Conversation[],
    thisWeek: [] as Conversation[],
    older: [] as Conversation[]
  }

  const now = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const yesterday = new Date(today)
  yesterday.setDate(yesterday.getDate() - 1)
  const weekAgo = new Date(today)
  weekAgo.setDate(weekAgo.getDate() - 7)

  filteredConversations.forEach(conv => {
    const convDate = new Date(conv.timestamp)
    if (convDate >= today) {
      groupedConversations.today.push(conv)
    } else if (convDate >= yesterday) {
      groupedConversations.yesterday.push(conv)
    } else if (convDate >= weekAgo) {
      groupedConversations.thisWeek.push(conv)
    } else {
      groupedConversations.older.push(conv)
    }
  })

  const handleStartEdit = (conv: Conversation) => {
    setEditingId(conv.id)
    setEditTitle(conv.title)
  }

  const handleSaveEdit = (id: string) => {
    if (editTitle.trim()) {
      onRename(id, editTitle.trim())
    }
    setEditingId(null)
  }

  const ConversationItem = ({ conv }: { conv: Conversation }) => {
    const isActive = conv.id === activeId
    const isEditing = editingId === conv.id

    return (
      <div
        className={cn(
          'group relative p-3 rounded-lg cursor-pointer transition-all',
          'hover:bg-muted/50',
          isActive && 'bg-muted'
        )}
        onClick={() => !isEditing && onSelect(conv.id)}
      >
        <div className="flex items-start gap-2">
          <MessageSquare className="w-4 h-4 mt-0.5 flex-shrink-0 text-muted-foreground" />
          <div className="flex-1 min-w-0">
            {isEditing ? (
              <Input
                value={editTitle}
                onChange={(e) => setEditTitle(e.target.value)}
                onBlur={() => handleSaveEdit(conv.id)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleSaveEdit(conv.id)
                  if (e.key === 'Escape') setEditingId(null)
                }}
                className="h-7 text-sm"
                autoFocus
                onClick={(e) => e.stopPropagation()}
              />
            ) : (
              <h4 className="text-sm font-medium truncate">{conv.title}</h4>
            )}
            <p className="text-xs text-muted-foreground truncate mt-0.5">
              {conv.lastMessage}
            </p>
          </div>
          {conv.isPinned && (
            <Pin className="w-3 h-3 text-primary-600 flex-shrink-0" />
          )}
        </div>

        <div className="absolute right-2 top-2 opacity-0 group-hover:opacity-100 transition-opacity flex gap-1">
          <Button
            size="sm"
            variant="ghost"
            onClick={(e) => {
              e.stopPropagation()
              handleStartEdit(conv)
            }}
            className="h-6 w-6 p-0"
          >
            <Edit2 className="w-3 h-3" />
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={(e) => {
              e.stopPropagation()
              onDelete(conv.id)
            }}
            className="h-6 w-6 p-0 hover:text-destructive"
          >
            <Trash2 className="w-3 h-3" />
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className={cn('flex flex-col h-full bg-card border-l', className)}>
      {/* Header */}
      <div className="p-4 border-b">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-semibold">Conversations</h3>
          <Button size="sm" onClick={onNew} className="h-8 gap-1">
            <Plus className="w-4 h-4" />
            New
          </Button>
        </div>

        {/* Search */}
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            placeholder="Search conversations..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-8 h-9"
          />
        </div>
      </div>

      {/* Conversations List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-6">
        {groupedConversations.today.length > 0 && (
          <div>
            <h4 className="text-xs font-medium text-muted-foreground mb-2 px-2">Today</h4>
            <div className="space-y-1">
              {groupedConversations.today.map(conv => (
                <ConversationItem key={conv.id} conv={conv} />
              ))}
            </div>
          </div>
        )}

        {groupedConversations.yesterday.length > 0 && (
          <div>
            <h4 className="text-xs font-medium text-muted-foreground mb-2 px-2">Yesterday</h4>
            <div className="space-y-1">
              {groupedConversations.yesterday.map(conv => (
                <ConversationItem key={conv.id} conv={conv} />
              ))}
            </div>
          </div>
        )}

        {groupedConversations.thisWeek.length > 0 && (
          <div>
            <h4 className="text-xs font-medium text-muted-foreground mb-2 px-2">Last 7 Days</h4>
            <div className="space-y-1">
              {groupedConversations.thisWeek.map(conv => (
                <ConversationItem key={conv.id} conv={conv} />
              ))}
            </div>
          </div>
        )}

        {groupedConversations.older.length > 0 && (
          <div>
            <h4 className="text-xs font-medium text-muted-foreground mb-2 px-2">Older</h4>
            <div className="space-y-1">
              {groupedConversations.older.map(conv => (
                <ConversationItem key={conv.id} conv={conv} />
              ))}
            </div>
          </div>
        )}

        {filteredConversations.length === 0 && (
          <div className="text-center py-8">
            <MessageSquare className="w-12 h-12 text-muted-foreground/30 mx-auto mb-2" />
            <p className="text-sm text-muted-foreground">
              {searchQuery ? 'No conversations found' : 'No conversations yet'}
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
