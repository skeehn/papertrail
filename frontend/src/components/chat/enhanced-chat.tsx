"use client"

import React, { useEffect, useRef, useState, useCallback } from 'react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Card } from '@/components/ui/card'
import { Brain, Upload, Send, FileText, X, Sparkles, User, Copy, Check, ThumbsUp, ThumbsDown, RefreshCw, Zap, Search, Network, Lightbulb, CheckCircle2, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { useDropzone } from 'react-dropzone'
import { useAgentChat, type AgentType } from '@/hooks/use-agent-chat'
import { useWebSocket } from '@/hooks/use-websocket'

const AGENT_LABELS: Record<AgentType, string> = {
  synthesizer: 'Synthesizer',
  critic: 'Critic',
  connector: 'Connector',
  reasoning: 'Reasoning',
}

const AGENT_ICONS: Record<AgentType, React.ComponentType<{ className?: string }>> = {
  synthesizer: Sparkles,
  critic: Lightbulb,
  connector: Network,
  reasoning: Zap,
}

const AGENT_DESCRIPTIONS: Record<AgentType, string> = {
  synthesizer: 'Synthesizes information from multiple sources',
  critic: 'Critically analyzes and evaluates claims',
  connector: 'Finds relationships and connections between concepts',
  reasoning: 'Performs complex multi-hop reasoning',
}

export default function EnhancedChat() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [uploadStatus, setUploadStatus] = useState<'idle' | 'uploading' | 'success' | 'error'>('idle')
  const [uploadProgress, setUploadProgress] = useState(0)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [processingId, setProcessingId] = useState<string | null>(null)
  const [processingStatus, setProcessingStatus] = useState<string | null>(null)
  const [processingMessage, setProcessingMessage] = useState<string | null>(null)
  const [input, setInput] = useState('')
  const [copiedMessageId, setCopiedMessageId] = useState<string | null>(null)
  const [messageFeedback, setMessageFeedback] = useState<Record<string, 'liked' | 'disliked' | null>>({})
  const uploadAbortRef = useRef<AbortController | null>(null)
  const fileInputRef = useRef<HTMLInputElement | null>(null)
  const messagesEndRef = useRef<HTMLDivElement | null>(null)
  const textareaRef = useRef<HTMLTextAreaElement | null>(null)
  const formRef = useRef<HTMLFormElement | null>(null)

  const {
    messages,
    isLoading,
    error: chatError,
    selectedAgent,
    setSelectedAgent,
    sendMessage,
    clearMessages,
  } = useAgentChat()

  // WebSocket for real-time processing updates
  const { isConnected, subscribe, lastMessage } = useWebSocket({
    autoConnect: true,
  })

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, isLoading])

  const handleCopyMessage = async (messageId: string, content: string) => {
    try {
      await navigator.clipboard.writeText(content)
      setCopiedMessageId(messageId)
      setTimeout(() => setCopiedMessageId(null), 2000)
    } catch (err) {
      console.error('Failed to copy message:', err)
    }
  }

  const handleMessageFeedback = (messageId: string, feedback: 'liked' | 'disliked') => {
    setMessageFeedback((prev: Record<string, 'liked' | 'disliked' | null>) => ({
      ...prev,
      [messageId]: prev[messageId] === feedback ? null : feedback
    }))
  }

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (input?.trim() && !isLoading) {
      sendMessage(input)
      setInput('')
    }
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value)
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

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const file = acceptedFiles[0]
    if (!file) return

    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setUploadStatus('error')
      setUploadError('Only PDF files are supported.')
      return
    }

    setSelectedFile(file)
    setUploadStatus('idle')
    setUploadProgress(0)
    setUploadError(null)
    setProcessingId(null)
    setProcessingStatus(null)
    setProcessingMessage(null)
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf']
    },
    multiple: false,
    noClick: false,
  })

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

      const response = await fetch('/api/papers/upload', {
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

  // Subscribe to processing updates via WebSocket
  useEffect(() => {
    if (processingId && isConnected) {
      subscribe(`processing:${processingId}`)
    }
  }, [processingId, isConnected, subscribe])

  // Handle WebSocket messages for processing updates
  useEffect(() => {
    if (!lastMessage || !processingId) return

    const message = lastMessage
    if (message.data.processing_id !== processingId) return

    switch (message.type) {
      case 'processing_start':
        setProcessingStatus('pending')
        setProcessingMessage('Processing started...')
        break
      case 'processing_update':
        setProcessingStatus('processing')
        setProcessingMessage(message.data.message || 'Processing paper...')
        setUploadProgress((message.data.progress || 0) * 100)
        break
      case 'processing_complete':
        setProcessingStatus('completed')
        setProcessingMessage('Processing completed! You can now chat about this paper.')
        setUploadProgress(100)
        break
      case 'processing_error':
        setProcessingStatus('failed')
        setProcessingMessage(`Processing failed: ${message.data.error || 'Unknown error'}`)
        setUploadError(message.data.error || 'Processing failed')
        break
    }
  }, [lastMessage, processingId])

  // Fallback polling if WebSocket is not available
  useEffect(() => {
    if (!processingId || isConnected) return

    let isActive = true
    const pollInterval = 5000
    let intervalId: ReturnType<typeof setInterval> | null = null

    const pollProcessingStatus = async () => {
      try {
        const response = await fetch(`/api/papers/${processingId}`)
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
  }, [processingId, isConnected])

  return (
    <div className="flex flex-col h-full bg-background">
      <input
        ref={fileInputRef}
        type="file"
        accept="application/pdf"
        onChange={handleFileChange}
        className="hidden"
        aria-label="Upload PDF file"
      />

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-2xl mx-auto px-4 py-8 md:py-12 space-y-8">
          {messages.length === 0 && (
            <div className="flex items-center justify-center min-h-[50vh]">
              <div className="text-center max-w-md space-y-6">
                <div className="w-12 h-12 bg-foreground text-background rounded-full flex items-center justify-center mx-auto">
                  <Brain className="w-6 h-6" />
                </div>
                <div className="space-y-2">
                  <h2 className="text-2xl font-semibold">Welcome to PaperTrail</h2>
                  <p className="text-muted-foreground">
                    Your intelligent research assistant for analyzing scientific literature
                  </p>
                </div>
                <div className="text-left bg-muted/30 rounded-lg p-6 space-y-3 border border-border/50">
                  <p className="text-sm font-medium">You can ask me to:</p>
                  <ul className="text-sm text-muted-foreground space-y-2">
                    <li>• Search and analyze your research papers</li>
                    <li>• Extract claims and insights from literature</li>
                    <li>• Find relationships between papers</li>
                    <li>• Identify contradictions and research gaps</li>
                  </ul>
                </div>
              </div>
            </div>
          )}

          {messages.map((message, index) => {
            const AgentIcon = message.agentType ? AGENT_ICONS[message.agentType] : Sparkles
            const isCopied = copiedMessageId === message.id
            const feedback = messageFeedback[message.id]
            
            return (
              <div
                key={message.id}
                className={cn(
                  'flex gap-4 group',
                  message.role === 'user' ? 'justify-end' : 'justify-start',
                  'animate-in fade-in slide-in-from-bottom-4 duration-500'
                )}
                // eslint-disable-next-line react/forbid-dom-props
                style={{ '--animation-delay': index * 50 } as React.CSSProperties}
              >
                {message.role === 'assistant' && (
                  <div className="w-8 h-8 rounded-full bg-foreground text-background flex items-center justify-center flex-shrink-0">
                    <AgentIcon className="w-4 h-4" />
                  </div>
                )}

                <div
                  className={cn(
                    'rounded-lg px-4 py-3 max-w-[80%] relative transition-colors',
                    message.role === 'user'
                      ? 'bg-foreground text-background'
                      : 'bg-muted/50 border border-border/50'
                  )}
                >
                  {message.role === 'assistant' ? (
                    <div>
                      {message.agentType && (
                        <div className="flex items-center gap-2 mb-2">
                          <span className="text-xs font-medium text-muted-foreground capitalize flex items-center gap-1">
                            <AgentIcon className="w-3 h-3" />
                            {message.agentType} Agent
                          </span>
                        </div>
                      )}
                      <div className="prose prose-sm dark:prose-invert max-w-none prose-headings:font-semibold prose-code:bg-muted prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-pre:bg-muted prose-pre:border">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {message.content}
                        </ReactMarkdown>
                      </div>
                      <div className="flex items-center gap-1 mt-3 opacity-0 group-hover:opacity-100 transition-opacity duration-200 pt-2 border-t">
                        <Button
                          size="sm"
                          variant="ghost"
                          className="h-7 px-2 hover:bg-muted"
                          onClick={() => handleCopyMessage(message.id, message.content)}
                          title="Copy message"
                        >
                          {isCopied ? (
                            <Check className="w-3.5 h-3.5 text-green-600" />
                          ) : (
                            <Copy className="w-3.5 h-3.5" />
                          )}
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          className={cn("h-7 px-2 hover:bg-muted transition-colors", feedback === 'liked' && "text-green-600 bg-green-50 dark:bg-green-950")}
                          onClick={() => handleMessageFeedback(message.id, 'liked')}
                          title="Like this response"
                        >
                          <ThumbsUp className="w-3.5 h-3.5" />
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          className={cn("h-7 px-2 hover:bg-muted transition-colors", feedback === 'disliked' && "text-red-600 bg-red-50 dark:bg-red-950")}
                          onClick={() => handleMessageFeedback(message.id, 'disliked')}
                          title="Dislike this response"
                        >
                          <ThumbsDown className="w-3.5 h-3.5" />
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <p className="text-sm">
                      {message.content}
                    </p>
                  )}
                </div>

                {message.role === 'user' && (
                  <div className="w-8 h-8 rounded-full bg-muted flex items-center justify-center flex-shrink-0">
                    <User className="w-4 h-4 text-muted-foreground" />
                  </div>
                )}
              </div>
            )
          })}

          {isLoading && (
            <div className="flex gap-4">
              <div className="w-8 h-8 rounded-full bg-foreground text-background flex items-center justify-center flex-shrink-0">
                <Sparkles className="w-4 h-4" />
              </div>
              <div className="bg-muted/50 border border-border/50 rounded-lg px-4 py-3">
                <div className="flex items-center gap-2">
                  <div className="flex gap-1">
                    {/* eslint-disable-next-line react/forbid-dom-props */}
                    <div className="w-2 h-2 bg-muted-foreground/50 rounded-full animate-bounce" style={{ '--animation-delay': 0 } as React.CSSProperties}></div>
                    {/* eslint-disable-next-line react/forbid-dom-props */}
                    <div className="w-2 h-2 bg-muted-foreground/50 rounded-full animate-bounce" style={{ '--animation-delay': 150 } as React.CSSProperties}></div>
                    {/* eslint-disable-next-line react/forbid-dom-props */}
                    <div className="w-2 h-2 bg-muted-foreground/50 rounded-full animate-bounce" style={{ '--animation-delay': 300 } as React.CSSProperties}></div>
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
          <div className="flex gap-3 items-center">
            <span className="text-sm font-medium">Agent:</span>
            <div className="flex gap-2 flex-wrap">
              {(Object.keys(AGENT_LABELS) as AgentType[]).map((agent) => {
                const Icon = AGENT_ICONS[agent]
                const isSelected = selectedAgent === agent
                return (
                  <button
                    key={agent}
                    type="button"
                    onClick={() => setSelectedAgent(agent)}
                    className={cn(
                      "flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200",
                      isSelected
                        ? "bg-primary-500 text-primary-foreground shadow-md"
                        : "bg-muted hover:bg-muted/80 text-muted-foreground"
                    )}
                    title={AGENT_DESCRIPTIONS[agent]}
                  >
                    <Icon className="w-4 h-4" />
                    <span>{AGENT_LABELS[agent]}</span>
                  </button>
                )
              })}
            </div>
          </div>
          <form ref={formRef} onSubmit={onSubmit} className="relative">
          <Textarea
            ref={textareaRef}
            value={input}
            onChange={handleInputChange}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                if (input?.trim() && !isLoading) {
                  formRef.current?.requestSubmit()
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

          {/* Drag and Drop Zone - Minimal */}
          {!selectedFile && uploadStatus === 'idle' && (
            <div
              {...getRootProps()}
              className={cn(
                "border border-dashed rounded-lg p-6 text-center transition-colors cursor-pointer",
                isDragActive
                  ? "border-foreground bg-muted/50"
                  : "border-border hover:border-foreground/50 hover:bg-muted/30"
              )}
            >
              <input {...getInputProps()} />
              <Upload className={cn(
                "w-6 h-6 mx-auto mb-2 transition-colors",
                isDragActive ? "text-foreground" : "text-muted-foreground"
              )} />
              <p className="text-xs text-muted-foreground">
                {isDragActive ? "Drop PDF here" : "Drag & drop a PDF or click to browse"}
              </p>
            </div>
          )}

          {(selectedFile || uploadStatus !== 'idle' || processingId || uploadError) && (
            <Card className={cn(
              "p-4 transition-all duration-300",
              uploadStatus === 'success' && "border-green-500/50 bg-green-500/5",
              uploadStatus === 'error' && "border-destructive/50 bg-destructive/5"
            )}>
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-3 text-sm min-w-0 flex-1">
                  {uploadStatus === 'success' ? (
                    <CheckCircle2 className="w-5 h-5 text-green-600 flex-shrink-0" />
                  ) : uploadStatus === 'uploading' ? (
                    <Loader2 className="w-5 h-5 text-primary-500 flex-shrink-0 animate-spin" />
                  ) : (
                    <FileText className="w-5 h-5 text-primary-600 flex-shrink-0" />
                  )}
                  <div className="min-w-0 flex-1">
                    <span className="font-medium truncate block">
                      {selectedFile ? selectedFile.name : 'No file selected'}
                    </span>
                    {selectedFile && (
                      <span className="text-xs text-muted-foreground">
                        {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB
                      </span>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-2 flex-shrink-0">
                  {uploadStatus !== 'uploading' && selectedFile && uploadStatus !== 'success' && (
                    <Button size="sm" onClick={handleUpload} className="gap-2">
                      <Upload className="w-4 h-4" />
                      Upload
                    </Button>
                  )}
                  {uploadStatus === 'uploading' && (
                    <Button size="sm" variant="outline" onClick={handleCancelUpload} className="gap-2">
                      <X className="w-4 h-4" />
                      Cancel
                    </Button>
                  )}
                  {uploadStatus !== 'uploading' && (
                    <Button size="sm" variant="ghost" onClick={resetUploadState}>
                      <X className="w-4 h-4" />
                    </Button>
                  )}
                </div>
              </div>

              {(uploadStatus === 'uploading' || uploadProgress > 0) && (
                <div className="mt-3 space-y-2">
                  <div className="h-2 w-full bg-muted rounded-full overflow-hidden">
                    {/* eslint-disable-next-line react/forbid-dom-props */}
                    <div
                      className="h-full bg-primary-500 transition-all duration-500 rounded-full"
                      style={{ width: `${Math.max(0, Math.min(100, uploadProgress))}%` } as React.CSSProperties}
                    ></div>
                  </div>
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-muted-foreground">
                      {uploadStatus === 'uploading'
                        ? `Uploading... ${Math.round(uploadProgress)}%`
                        : uploadStatus === 'success'
                          ? 'Upload complete!'
                          : 'Ready to upload'}
                    </span>
                    {processingStatus && (
                      <span className="text-primary-600 font-medium capitalize">
                        {processingStatus}
                      </span>
                    )}
                  </div>
                </div>
              )}

              {processingMessage && uploadStatus !== 'error' && (
                <div className="mt-3 flex items-start gap-2">
                  <Loader2 className="w-4 h-4 text-primary-500 animate-spin flex-shrink-0 mt-0.5" />
                  <p className="text-sm text-muted-foreground">{processingMessage}</p>
                </div>
              )}

              {uploadStatus === 'error' && uploadError && (
                <div className="mt-3 p-3 bg-destructive/10 border border-destructive/20 rounded-lg">
                  <p className="text-sm text-destructive font-medium">{uploadError}</p>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      resetUploadState()
                      fileInputRef.current?.click()
                    }}
                    className="mt-2"
                  >
                    Try Again
                  </Button>
                </div>
              )}

              {uploadStatus === 'success' && !processingId && (
                <div className="mt-3 flex items-center gap-2 text-sm text-green-600">
                  <CheckCircle2 className="w-4 h-4" />
                  <span>File uploaded successfully! You can now chat about this paper.</span>
                </div>
              )}
            </Card>
          )}

          <p className="text-xs text-center text-muted-foreground">
            Press Enter to send, Shift+Enter for new line
          </p>

          {chatError && (
            <div className="bg-muted/30 border border-border rounded-lg p-4 text-center">
              <p className="text-sm text-foreground font-medium mb-3">{chatError}</p>
              <div className="flex gap-2 justify-center">
                <Button 
                  size="sm" 
                  onClick={() => {
                    if (messages.length > 0) {
                      const lastUserMessage = [...messages].reverse().find(m => m.role === 'user')
                      if (lastUserMessage) {
                        sendMessage(lastUserMessage.content)
                      }
                    }
                  }}
                  className="gap-2 bg-foreground text-background hover:bg-foreground/90"
                >
                  <RefreshCw className="w-4 h-4" />
                  Retry
                </Button>
                <Button 
                  size="sm" 
                  variant="outline"
                  onClick={() => window.location.reload()}
                >
                  Reload Page
                </Button>
              </div>
            </div>
          )}

          {messages.length > 0 && (
            <div className="text-center">
              <Button size="sm" variant="outline" onClick={clearMessages}>
                Clear Conversation
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

