"use client"

import React, { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Check, Copy } from 'lucide-react'
import { cn } from '@/lib/utils'

interface CodeBlockProps {
  language?: string
  code: string
  filename?: string
  className?: string
}

export function CodeBlock({ language, code, filename, className }: CodeBlockProps) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    await navigator.clipboard.writeText(code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className={cn('relative group rounded-lg overflow-hidden', className)}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 bg-muted/50 border-b">
        <div className="flex items-center gap-2">
          {filename && (
            <span className="text-xs font-medium text-foreground">{filename}</span>
          )}
          {language && !filename && (
            <span className="text-xs font-medium text-muted-foreground">{language}</span>
          )}
        </div>
        <Button
          size="sm"
          variant="ghost"
          onClick={handleCopy}
          className="h-7 gap-1.5 opacity-0 group-hover:opacity-100 transition-opacity"
        >
          {copied ? (
            <>
              <Check className="w-3.5 h-3.5" />
              <span className="text-xs">Copied!</span>
            </>
          ) : (
            <>
              <Copy className="w-3.5 h-3.5" />
              <span className="text-xs">Copy</span>
            </>
          )}
        </Button>
      </div>

      {/* Code */}
      <pre className="p-4 overflow-x-auto bg-muted/30">
        <code className={cn('text-sm font-mono', language && `language-${language}`)}>
          {code}
        </code>
      </pre>
    </div>
  )
}
