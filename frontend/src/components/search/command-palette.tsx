"use client"

import React, { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import {
  Search,
  FileText,
  MessageSquare,
  Lightbulb,
  Network,
  Settings,
  Home,
  ClipboardList
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { Input } from '@/components/ui/input'

interface CommandItem {
  id: string
  title: string
  description?: string
  icon: React.ReactNode
  action: () => void
  category: 'navigation' | 'papers' | 'conversations' | 'claims' | 'actions'
}

interface CommandPaletteProps {
  isOpen: boolean
  onClose: () => void
}

export function CommandPalette({ isOpen, onClose }: CommandPaletteProps) {
  const [query, setQuery] = useState('')
  const [selectedIndex, setSelectedIndex] = useState(0)
  const router = useRouter()

  // Sample commands - in real app, these would be dynamic
  const allCommands: CommandItem[] = [
    {
      id: 'nav-dashboard',
      title: 'Dashboard',
      description: 'Go to dashboard',
      icon: <Home className="w-4 h-4" />,
      action: () => router.push('/dashboard'),
      category: 'navigation'
    },
    {
      id: 'nav-chat',
      title: 'Chat',
      description: 'Start a new conversation',
      icon: <MessageSquare className="w-4 h-4" />,
      action: () => router.push('/'),
      category: 'navigation'
    },
    {
      id: 'nav-papers',
      title: 'Papers Library',
      description: 'Browse your research papers',
      icon: <FileText className="w-4 h-4" />,
      action: () => router.push('/papers'),
      category: 'navigation'
    },
    {
      id: 'nav-graph',
      title: 'Knowledge Graph',
      description: 'Explore connections',
      icon: <Network className="w-4 h-4" />,
      action: () => router.push('/graph'),
      category: 'navigation'
    },
    {
      id: 'nav-audit',
      title: 'Audit Trail',
      description: 'View activity log',
      icon: <ClipboardList className="w-4 h-4" />,
      action: () => router.push('/audit'),
      category: 'navigation'
    },
    {
      id: 'nav-settings',
      title: 'Settings',
      description: 'Manage preferences',
      icon: <Settings className="w-4 h-4" />,
      action: () => router.push('/settings'),
      category: 'navigation'
    }
  ]

  const filteredCommands = allCommands.filter(cmd =>
    cmd.title.toLowerCase().includes(query.toLowerCase()) ||
    cmd.description?.toLowerCase().includes(query.toLowerCase())
  )

  useEffect(() => {
    setSelectedIndex(0)
  }, [query])

  useEffect(() => {
    if (!isOpen) return

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose()
      } else if (e.key === 'ArrowDown') {
        e.preventDefault()
        setSelectedIndex(prev => Math.min(prev + 1, filteredCommands.length - 1))
      } else if (e.key === 'ArrowUp') {
        e.preventDefault()
        setSelectedIndex(prev => Math.max(prev - 1, 0))
      } else if (e.key === 'Enter' && filteredCommands[selectedIndex]) {
        e.preventDefault()
        filteredCommands[selectedIndex].action()
        onClose()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, selectedIndex, filteredCommands, onClose])

  if (!isOpen) return null

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-background/80 backdrop-blur-sm z-50 animate-fade-in"
        onClick={onClose}
      />

      {/* Command Palette */}
      <div className="fixed top-[20%] left-1/2 -translate-x-1/2 w-full max-w-2xl z-50 animate-scale-in">
        <div className="bg-card border rounded-lg shadow-large overflow-hidden">
          {/* Search Input */}
          <div className="p-4 border-b">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
              <Input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search for papers, conversations, or navigate..."
                className="pl-10 h-12 text-base"
                autoFocus
              />
            </div>
          </div>

          {/* Results */}
          <div className="max-h-[400px] overflow-y-auto p-2">
            {filteredCommands.length === 0 ? (
              <div className="py-8 text-center">
                <p className="text-sm text-muted-foreground">No results found</p>
              </div>
            ) : (
              <div className="space-y-1">
                {filteredCommands.map((cmd, index) => (
                  <button
                    key={cmd.id}
                    onClick={() => {
                      cmd.action()
                      onClose()
                    }}
                    className={cn(
                      'w-full flex items-center gap-3 px-3 py-2.5 rounded-md transition-colors text-left',
                      'hover:bg-muted',
                      index === selectedIndex && 'bg-muted'
                    )}
                  >
                    <div className="flex-shrink-0 text-muted-foreground">
                      {cmd.icon}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-sm">{cmd.title}</div>
                      {cmd.description && (
                        <div className="text-xs text-muted-foreground truncate">
                          {cmd.description}
                        </div>
                      )}
                    </div>
                    {index === selectedIndex && (
                      <div className="text-xs text-muted-foreground">↵</div>
                    )}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="px-4 py-2 border-t bg-muted/30 flex items-center justify-between text-xs text-muted-foreground">
            <div className="flex gap-4">
              <span>↑↓ Navigate</span>
              <span>↵ Select</span>
              <span>Esc Close</span>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}

// Hook to manage command palette
export function useCommandPalette() {
  const [isOpen, setIsOpen] = useState(false)

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        setIsOpen(prev => !prev)
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  return {
    isOpen,
    open: () => setIsOpen(true),
    close: () => setIsOpen(false),
    toggle: () => setIsOpen(prev => !prev)
  }
}
