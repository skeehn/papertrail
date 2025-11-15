"use client"

import React, { useEffect, useRef, useState } from 'react'
import { useChat } from '@ai-sdk/react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Card } from '@/components/ui/card'
import { Brain, Upload, Send, FileText, X, Sparkles, User } from 'lucide-react'
import { cn } from '@/lib/utils'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

export default function EnhancedChat() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [uploadStatus, setUploadStatus] = useState<'idle' | 'uploading' | 'success' | 'error'>('idle')
  const [uploadProgress, setUploadProgress] = useState(0)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [processingId, setProcessingId] = useState<string | null>(null)
  const [processingStatus, setProcessingStatus] = useState<string | null>(null)
  const [processingMessage, setProcessingMessage] = useState<string | null>(null)
  const uploadAbortRef = useRef<AbortController | null>(null)
  const fileInputRef = useRef<HTMLInputElement | null>(null)
  const messagesEndRef = useRef<HTMLDivElement | null>(null)
  const textareaRef = useRef<HTMLTextAreaElement | null>(null)

  const chat = useChat()
  const messages = chat.messages
  const input = (chat as any).input as string
  const handleInputChange = (chat as any).handleInputChange as (e: React.ChangeEvent<HTMLTextAreaElement>) => void
  const handleSubmit = (chat as any).handleSubmit as (e: React.FormEvent) => void
  const isLoading = (chat as any).isLoading as boolean

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, isLoading])

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (input?.trim() && !isLoading && handleSubmit) {
      handleSubmit(e)
    }
  }

  const resetUploadState = () => {
    setSelectedFile(null)
    setUploadStatus('idle')
    setUploadProgress(0)
    setUploadError(null)
    setProcessingId(null)
    setProcessingStatus(null)
    setProcessingMessage(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) {
      resetUploadState()
      return
    }

    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setUploadStatus('error')
      setUploadError('Only PDF files are supported. Please select a PDF document.')
      setSelectedFile(null)
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
      return
    }

    setSelectedFile(file)
    setUploadStatus('idle')
    setUploadProgress(0)
    setUploadError(null)
    setProcessingId(null)
    setProcessingStatus(null)
    setProcessingMessage(null)
  }

  const handleUpload = async () => {
    if (!selectedFile) return

    const abortController = new AbortController()
    uploadAbortRef.current = abortController

    setUploadStatus('uploading')
    setUploadProgress(0)
    setUploadError(null)
    setProcessingId(null)
    setProcessingStatus(null)
    setProcessingMessage('Starting upload...')

    try {
      const formData = new FormData()
      formData.append('file', selectedFile)

      setUploadProgress(25)

      const response = await fetch('/api/v1/papers/upload', {
        method: 'POST',
        body: formData,
        signal: abortController.signal,
      })

      let data: any = null
      try {
        data = await response.json()
      } catch {
        // Ignore JSON parse errors
      }

      if (!response.ok) {
        const errorMessage =
          data?.detail ||
          data?.error ||
          response.statusText ||
          'Failed to upload the PDF. Please try again.'
        throw new Error(errorMessage)
      }

      if (!data) {
        throw new Error('Unexpected response from the server. Please try again later.')
      }

      const processingIdentifier = (data.processing_id as string | undefined) ?? null
      const initialStatus = (data.status as string | undefined) ?? null

      setUploadProgress(100)
      setUploadStatus('success')
      setProcessingId(processingIdentifier)
      setProcessingStatus(initialStatus)
      setProcessingMessage(
        processingIdentifier
          ? 'Paper uploaded successfully. Processing in progress...'
          : 'Paper uploaded successfully.'
      )
    } catch (error) {
      if ((error as Error).name === 'AbortError') {
        setProcessingMessage('Upload cancelled.')
        setUploadStatus('idle')
        setUploadProgress(0)
        setProcessingId(null)
        setProcessingStatus(null)
      } else {
        setUploadStatus('error')
        setUploadError(
          (error as Error).message || 'Something went wrong while uploading the paper.'
        )
        setUploadProgress(0)
        setProcessingMessage(null)
        setProcessingId(null)
        setProcessingStatus(null)
      }
    } finally {
      uploadAbortRef.current = null
    }
  }

  const handleCancelUpload = () => {
    if (uploadAbortRef.current) {
      uploadAbortRef.current.abort()
    }
  }

  useEffect(() => {
    if (!processingId) return

    let isActive = true
    const pollInterval = 5000
    let intervalId: ReturnType<typeof setInterval> | null = null

    const pollProcessingStatus = async () => {
      try {
        const response = await fetch(`/api/v1/papers/${processingId}`)
        if (!isActive) return

        if (!response.ok) {
          if (response.status === 404) {
            setProcessingMessage('Processing started. Waiting for updates...')
          }
          return
        }

        const data = await response.json()
        const status = (data.status as string | undefined) ?? null

        if (status) {
          setProcessingStatus(status)

          if (status === 'completed') {
            setProcessingMessage('Processing completed! You can now chat about this paper.')
            isActive = false
            if (intervalId) clearInterval(intervalId)
          } else if (status === 'failed') {
            setProcessingMessage('Processing failed. Please try again.')
            isActive = false
            if (intervalId) clearInterval(intervalId)
          } else if (status === 'processing') {
            setProcessingMessage('Processing paper...')
          } else if (status === 'pending') {
            setProcessingMessage('Paper received. Processing will begin shortly...')
          }
        }
      } catch {
        if (isActive) {
          setProcessingMessage('Waiting for updates...')
        }
      }
    }

    pollProcessingStatus()
    intervalId = setInterval(() => {
      if (isActive) pollProcessingStatus()
    }, pollInterval)

    return () => {
      isActive = false
      if (intervalId) clearInterval(intervalId)
    }
  }, [processingId])

  return (
    <div className="flex flex-col h-full bg-background">
      <input
        ref={fileInputRef}
        type="file"
        accept="application/pdf"
        onChange={handleFileChange}
        className="hidden"
      />

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-3xl mx-auto px-4 py-6 space-y-6">
          {messages.length === 0 && (
            <div className="flex items-center justify-center min-h-[50vh]">
              <div className="text-center max-w-md">
                <div className="w-16 h-16 bg-gradient-to-br from-primary-500 to-primary-700 rounded-2xl flex items-center justify-center mx-auto mb-4">
                  <Brain className="w-8 h-8 text-white" />
                </div>
                <h2 className="text-2xl font-semibold mb-2">Welcome to PaperTrail</h2>
                <p className="text-muted-foreground mb-6">
                  Your intelligent research assistant for analyzing scientific literature
                </p>
                <div className="text-left bg-card border rounded-lg p-4 space-y-2">
                  <p className="text-sm font-medium">You can ask me to:</p>
                  <ul className="text-sm text-muted-foreground space-y-1">
                    <li>• Search and analyze your research papers</li>
                    <li>• Extract claims and insights from literature</li>
                    <li>• Find relationships between papers</li>
                    <li>• Identify contradictions and research gaps</li>
                  </ul>
                </div>
              </div>
            </div>
          )}

          {messages.map((message) => (
            <div
              key={message.id}
              className={cn(
                'flex gap-4 animate-fade-in',
                message.role === 'user' ? 'justify-end' : 'justify-start'
              )}
            >
              {message.role === 'assistant' && (
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center flex-shrink-0">
                  <Sparkles className="w-4 h-4 text-white" />
                </div>
              )}

              <div
                className={cn(
                  'rounded-2xl px-4 py-3 max-w-[80%]',
                  message.role === 'user'
                    ? 'bg-primary-500 text-primary-foreground'
                    : 'bg-card border'
                )}
              >
                {message.role === 'assistant' ? (
                  <div className="prose prose-sm dark:prose-invert max-w-none">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {Array.isArray((message as any).parts)
                        ? (message as any).parts
                            .filter((p: any) => p && (typeof p === 'string' || p.type === 'text'))
                            .map((p: any) => (typeof p === 'string' ? p : p.text))
                            .join('')
                        : (message as any).content ?? ''}
                    </ReactMarkdown>
                  </div>
                ) : (
                  <p className="text-sm">
                    {Array.isArray((message as any).parts)
                      ? (message as any).parts
                          .filter((p: any) => p && (typeof p === 'string' || p.type === 'text'))
                          .map((p: any) => (typeof p === 'string' ? p : p.text))
                          .join('')
                      : (message as any).content ?? ''}
                  </p>
                )}
              </div>

              {message.role === 'user' && (
                <div className="w-8 h-8 rounded-full bg-muted flex items-center justify-center flex-shrink-0">
                  <User className="w-4 h-4 text-muted-foreground" />
                </div>
              )}
            </div>
          ))}

          {isLoading && (
            <div className="flex gap-4 animate-fade-in">
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center flex-shrink-0">
                <Sparkles className="w-4 h-4 text-white" />
              </div>
              <div className="bg-card border rounded-2xl px-4 py-3">
                <div className="flex items-center gap-2">
                  <div className="flex gap-1">
                    <div className="w-2 h-2 bg-muted-foreground/50 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                    <div className="w-2 h-2 bg-muted-foreground/50 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                    <div className="w-2 h-2 bg-muted-foreground/50 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                  </div>
                  <span className="text-sm text-muted-foreground">Thinking...</span>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input Area */}
      <div className="border-t bg-card/50 backdrop-blur-sm">
        <div className="max-w-3xl mx-auto px-4 py-4 space-y-3">
          <form onSubmit={onSubmit} className="relative">
            <Textarea
              ref={textareaRef}
              value={input}
              onChange={handleInputChange}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  if (input?.trim() && !isLoading) {
                    onSubmit(e as any)
                  }
                }
              }}
              placeholder="Ask about your research papers..."
              className="min-h-[60px] max-h-[200px] resize-none pr-24 rounded-xl"
              rows={2}
            />
            <div className="absolute right-2 bottom-2 flex items-center gap-2">
              <Button
                type="button"
                size="icon"
                variant="ghost"
                onClick={() => fileInputRef.current?.click()}
                disabled={uploadStatus === 'uploading'}
              >
                <Upload className="w-4 h-4" />
              </Button>
              <Button
                type="submit"
                size="icon"
                disabled={!input?.trim() || isLoading}
              >
                <Send className="w-4 h-4" />
              </Button>
            </div>
          </form>

          {(selectedFile || uploadStatus !== 'idle' || processingId || uploadError) && (
            <Card className="p-3">
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-2 text-sm min-w-0">
                  <FileText className="w-4 h-4 text-primary-600 flex-shrink-0" />
                  <span className="font-medium truncate">
                    {selectedFile ? selectedFile.name : 'No file selected'}
                  </span>
                  {selectedFile && (
                    <span className="text-xs text-muted-foreground flex-shrink-0">
                      {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-2 flex-shrink-0">
                  {uploadStatus !== 'uploading' && selectedFile && (
                    <Button size="sm" onClick={handleUpload}>
                      Upload
                    </Button>
                  )}
                  {uploadStatus === 'uploading' && (
                    <Button size="sm" variant="outline" onClick={handleCancelUpload}>
                      Cancel
                    </Button>
                  )}
                  <Button size="sm" variant="ghost" onClick={resetUploadState}>
                    <X className="w-4 h-4" />
                  </Button>
                </div>
              </div>

              {(uploadStatus === 'uploading' || uploadProgress > 0) && (
                <div className="mt-2">
                  <div className="h-1.5 w-full bg-muted rounded-full overflow-hidden">
                    <div
                      className="h-full bg-primary-500 transition-all duration-500"
                      style={{ width: `${uploadProgress}%` }}
                    ></div>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    {uploadStatus === 'uploading'
                      ? `Uploading... ${Math.round(uploadProgress)}%`
                      : uploadStatus === 'success'
                        ? 'Upload complete!'
                        : 'Ready to upload'}
                  </p>
                </div>
              )}

              {uploadStatus === 'error' && uploadError && (
                <p className="text-sm text-destructive mt-2">{uploadError}</p>
              )}

              {processingMessage && (
                <p className="text-xs text-muted-foreground mt-2">{processingMessage}</p>
              )}
            </Card>
          )}

          <p className="text-xs text-center text-muted-foreground">
            Press Enter to send, Shift+Enter for new line
          </p>
        </div>
      </div>
    </div>
  )
}
