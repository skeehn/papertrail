"use client"

import React, { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Check, Copy, RotateCcw, Edit2, Share2 } from 'lucide-react'
import { cn } from '@/lib/utils'

interface MessageActionsProps {
  content: string
  onRegenerate?: () => void
  onEdit?: () => void
  className?: string
}

export function MessageActions({ content, onRegenerate, onEdit, className }: MessageActionsProps) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    await navigator.clipboard.writeText(content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className={cn(
      'flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity',
      className
    )}>
      <Button
        size="sm"
        variant="ghost"
        onClick={handleCopy}
        className="h-7 w-7 p-0"
        title="Copy message"
      >
        {copied ? (
          <Check className="w-3.5 h-3.5 text-green-600" />
        ) : (
          <Copy className="w-3.5 h-3.5" />
        )}
      </Button>

      {onRegenerate && (
        <Button
          size="sm"
          variant="ghost"
          onClick={onRegenerate}
          className="h-7 w-7 p-0"
          title="Regenerate response"
        >
          <RotateCcw className="w-3.5 h-3.5" />
        </Button>
      )}

      {onEdit && (
        <Button
          size="sm"
          variant="ghost"
          onClick={onEdit}
          className="h-7 w-7 p-0"
          title="Edit message"
        >
          <Edit2 className="w-3.5 h-3.5" />
        </Button>
      )}

      <Button
        size="sm"
        variant="ghost"
        className="h-7 w-7 p-0"
        title="Share message"
      >
        <Share2 className="w-3.5 h-3.5" />
      </Button>
    </div>
  )
}
