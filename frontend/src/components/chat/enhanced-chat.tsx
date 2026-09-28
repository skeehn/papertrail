"use client"

import React, { useCallback, useEffect, useRef, useState } from 'react'
import { useChat } from '@ai-sdk/react'
import { DefaultChatTransport } from 'ai'
import type { UIMessage } from 'ai'
import {
  Brain, Paperclip, ArrowUp, FileText, X, Copy, Check, RefreshCw,
  CheckCircle2, Loader2, Plus, ChevronDown, Search, BookPlus, Square,
  ChevronRight, TriangleAlert,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'
import { useDropzone } from 'react-dropzone'
import { CHAT_MODELS, DEFAULT_MODEL_ID, getModel } from '@/lib/chat-models'
import {
  conversationStore,
  newConversationId,
} from '@/lib/conversations'

const SUGGESTIONS = [
  'What papers do I have on graph neural networks?',
  'Summarize the Recursive Language Models paper',
  'Find contradictions or gaps across my papers',
  'Index arxiv.org/abs/2512.24601',
]

function textOf(m: UIMessage): string {
  return (m.parts ?? [])
    .filter((p): p is { type: 'text'; text: string } => p.type === 'text')
    .map((p) => p.text)
    .join('')
}

function reasoningOf(m: UIMessage): string {
  return (m.parts ?? [])
    .filter((p: any) => p?.type === 'reasoning')
    .map((p: any) => p.text ?? '')
    .join('')
    .trim()
}

/* ---------------- Tool chips ---------------- */

interface ToolPartLike {
  type: string
  state?: string
  input?: any
  output?: any
  errorText?: string
}

export function ToolChip({ part }: { part: ToolPartLike }) {
  const name = part.type.replace(/^tool-/, '')
  const Icon = name === 'indexArxiv' ? BookPlus : Search
  const isIndex = name === 'indexArxiv'
  const done = part.state === 'output-available'
  const errored = part.state === 'output-error'
  const count = done && part.output?.papers ? part.output.papers.length : null

  if (errored) {
    return (
      <div className="mb-2 flex items-center gap-1.5 text-xs text-destructive">
        <TriangleAlert className="h-3.5 w-3.5" />
        <span>
          {isIndex ? 'Indexing failed' : 'Search failed'}
          {part.errorText ? <span className="ml-1 opacity-70">{part.errorText}</span> : null}
        </span>
      </div>
    )
  }

  return (
    <div className="mb-2 flex items-center gap-1.5 text-xs text-muted-foreground">
      {done ? <Icon className="h-3.5 w-3.5 text-primary" /> : <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" />}
      {isIndex
        ? (done
          ? <span>Indexed <span className="text-foreground">{part.output?.title || part.output?.arxiv_id || 'paper'}</span></span>
          : <span>Indexing <span className="text-foreground">{part.input?.id_or_url || 'paper'}…</span></span>)
        : (done
          ? <span>Searched papers · <span className="text-foreground">{count ?? 0} found</span></span>
          : <span>Searching papers{part.input?.query ? <> for <span className="text-foreground">“{part.input.query}”</span></> : ''}…</span>)}
    </div>
  )
}

/* ---------------- Thinking block ---------------- */

function ThinkingBlock({ text, streaming }: { text: string; streaming: boolean }) {
  const [open, setOpen] = useState(false)
  if (!text) return null
  return (
    <div className="mb-3 rounded-xl border border-border/70 bg-muted/30 overflow-hidden">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-2 px-3 py-2 text-xs font-medium text-muted-foreground transition-colors hover:text-foreground"
      >
        {streaming
          ? <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" />
          : <Brain className="h-3.5 w-3.5" />}
        {streaming ? 'Thinking…' : 'Thought process'}
        <ChevronRight className={cn('ml-auto h-3.5 w-3.5 transition-transform', open && 'rotate-90')} />
      </button>
      {open && (
        <div className="border-t border-border/60 px-3 py-2.5 text-xs leading-relaxed text-muted-foreground whitespace-pre-wrap max-h-72 overflow-y-auto thin-scroll">
          {text}
        </div>
      )}
    </div>
  )
}

export default function EnhancedChat() {
  const [input, setInput] = useState('')
  const [modelId, setModelId] = useState<string>(DEFAULT_MODEL_ID)
  const [modelOpen, setModelOpen] = useState(false)
  const [copiedId, setCopiedId] = useState<string | null>(null)

  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [uploadStatus, setUploadStatus] = useState<'idle' | 'uploading' | 'success' | 'error'>('idle')
  const [uploadProgress, setUploadProgress] = useState(0)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [processingMessage, setProcessingMessage] = useState<string | null>(null)

  const fileInputRef = useRef<HTMLInputElement | null>(null)
  const messagesEndRef = useRef<HTMLDivElement | null>(null)
  const textareaRef = useRef<HTMLTextAreaElement | null>(null)
  const formRef = useRef<HTMLFormElement | null>(null)
  const uploadAbortRef = useRef<AbortController | null>(null)

  /* ---------------- Conversations state ---------------- */
  const [conversations, setConversations] = useState(
    () => (typeof window === 'undefined' ? [] : conversationStore.list())
  )
  const [activeId, setActiveId] = useState<string | null>(null)
  const activeIdRef = useRef<string | null>(null)
  const switchGuardRef = useRef<string | null>(null) // id we're currently restoring

  const refreshConversations = useCallback(() => {
    setConversations(conversationStore.list())
  }, [])

  useEffect(() => {
    refreshConversations()
    const unsub = conversationStore.subscribe(refreshConversations)
    const onStorage = (e: StorageEvent) => {
      if (!e.key || e.key === 'papertrail_conversations_index') refreshConversations()
    }
    window.addEventListener('storage', onStorage)
    return () => {
      unsub()
      window.removeEventListener('storage', onStorage)
    }
  }, [refreshConversations])

  const { messages, sendMessage, status, error, stop, setMessages, regenerate } = useChat({
    transport: new DefaultChatTransport({ api: '/api/chat' }),
    onFinish: () => {
      const id = activeIdRef.current
      if (id) conversationStore.save(id, messagesRef.current, { modelId: modelRef.current })
      refreshConversations()
    },
  })

  const isBusy = status === 'submitted' || status === 'streaming'
  const activeModel = getModel(modelId)
  const modelRef = useRef(modelId)
  modelRef.current = modelId
  const messagesRef = useRef(messages)
  messagesRef.current = messages

  const persistSnapshot = useCallback(
    (id: string | null, snapshot: UIMessage[]) => {
      if (!id) return
      conversationStore.save(id, snapshot, { modelId: modelRef.current })
      refreshConversations()
    },
    [refreshConversations]
  )

  /* Persist incrementally while streaming so interruptions are not lost */
  useEffect(() => {
    if (status !== 'streaming' && status !== 'submitted') return
    if (switchGuardRef.current) return
    persistSnapshot(activeIdRef.current, messages)
  }, [messages, status, persistSnapshot])

  /* Restore on first mount: explicit target (sidebar from another route)
     wins; otherwise resume the most recent conversation. */
  const restoredRef = useRef(false)
  useEffect(() => {
    if (restoredRef.current) return
    restoredRef.current = true
    let pendingId: string | null = null
    try {
      pendingId = sessionStorage.getItem('papertrail_open_conversation')
      sessionStorage.removeItem('papertrail_open_conversation')
    } catch { /* no sessionStorage */ }

    const list = conversationStore.list()
    setConversations(list)
    const target = (pendingId && list.find((c) => c.id === pendingId)) || list[0]
    if (target) {
      switchGuardRef.current = target.id
      activeIdRef.current = target.id
      setActiveId(target.id)
      setMessages(conversationStore.load(target.id))
      if (target.modelId) setModelId(target.modelId)
      switchGuardRef.current = null
    }
  }, [setMessages])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, status])

  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 220)}px`
  }, [input])

  /* Native window-capture listener instead of a React onKeyDown: delegated
     keydown was observably not delivered to this textarea (clicks fired,
     Enter did not). Refs and React state are deliberately avoided — they
     were observed to go stale across dev remounts. Do not "simplify" back
     to an inline onKeyDown without re-testing Enter. */
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== 'Enter' || e.shiftKey || e.isComposing || !e.cancelable) return
      const el = e.target as HTMLElement | null
      if (!el || el.tagName !== 'TEXTAREA') return
      const form = el.closest('form') as HTMLFormElement | null
      if (!form) return
      e.preventDefault()
      form.requestSubmit()
    }
    window.addEventListener('keydown', onKey, true)
    return () => window.removeEventListener('keydown', onKey, true)
  }, [])

  const onSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    // The composer's live DOM value is the source of truth: React state can
    // lag behind the textarea under some input-event paths.
    const ta = e.currentTarget.querySelector('textarea')
    const text = ta ? ta.value : input
    if (!text.trim() || isBusy) return

    // First message in a brand-new chat: mint an id before the request flies.
    if (!activeIdRef.current) {
      const id = newConversationId()
      activeIdRef.current = id
      setActiveId(id)
    }
    sendMessage({ text }, { body: { modelId } })
    if (ta) ta.value = ''
    setInput('')
  }

  const startNewChat = useCallback(() => {
    stop()
    setMessages([])
    activeIdRef.current = null
    setActiveId(null)
    setInput('')
  }, [stop, setMessages])

  const switchTo = useCallback(
    (id: string) => {
      if (id === activeIdRef.current) return
      stop()
      switchGuardRef.current = id
      activeIdRef.current = id
      setActiveId(id)
      setMessages(conversationStore.load(id))
      switchGuardRef.current = null
    },
    [stop, setMessages]
  )

  const deleteConversation = useCallback(
    (id: string) => {
      conversationStore.remove(id)
      refreshConversations()
      if (id === activeIdRef.current) startNewChat()
    },
    [refreshConversations, startNewChat]
  )

  const renameConversation = useCallback(
    (id: string, title: string) => {
      conversationStore.rename(id, title)
      refreshConversations()
    },
    [refreshConversations]
  )

  const togglePinConversation = useCallback(
    (id: string) => {
      conversationStore.togglePinned(id)
      refreshConversations()
    },
    [refreshConversations]
  )

  /* Expose sidebar actions globally (AppSidebar consumes these). */
  useEffect(() => {
    const w = window as any
    w.__papertrailChat = {
      conversations,
      activeId,
      startNewChat,
      switchTo,
      deleteConversation,
      renameConversation,
      togglePinConversation,
    }
    // Notify subscribers (sidebar) that the registry changed.
    window.dispatchEvent(new CustomEvent('papertrail:chat-registry'))
    return () => { delete (w as any).__papertrailChat }
  }, [conversations, activeId, startNewChat, switchTo, deleteConversation, renameConversation, togglePinConversation])

  /* ---------------- message helpers ---------------- */

  const copyMessage = async (id: string, text: string) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopiedId(id)
      setTimeout(() => setCopiedId(null), 2000)
    } catch { /* ignore */ }
  }

  /* ---------------- PDF upload ---------------- */

  const resetUpload = () => {
    setSelectedFile(null); setUploadStatus('idle'); setUploadProgress(0)
    setUploadError(null); setProcessingMessage(null)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const acceptFile = (file?: File | null) => {
    if (!file) return
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setUploadStatus('error'); setUploadError('Only PDF files are supported.')
      return
    }
    setSelectedFile(file); setUploadStatus('idle'); setUploadError(null)
  }

  const onDrop = useCallback((files: File[]) => acceptFile(files[0]), [])
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop, accept: { 'application/pdf': ['.pdf'] }, multiple: false, noClick: true, noKeyboard: true,
  })

  const handleUpload = async () => {
    if (!selectedFile) return
    const ac = new AbortController(); uploadAbortRef.current = ac
    setUploadStatus('uploading'); setUploadProgress(25); setProcessingMessage('Uploading…')
    try {
      const fd = new FormData(); fd.append('file', selectedFile)
      const res = await fetch('/api/papers/upload', { method: 'POST', body: fd, signal: ac.signal })
      const data = await res.json().catch(() => null)
      if (!res.ok) throw new Error(data?.detail || data?.error || 'Upload failed')
      setUploadProgress(100); setUploadStatus('success')
      setProcessingMessage('Uploaded. Processing in progress…')
    } catch (e) {
      if ((e as Error).name === 'AbortError') { resetUpload(); return }
      setUploadStatus('error'); setUploadError((e as Error).message); setProcessingMessage(null)
    } finally { uploadAbortRef.current = null }
  }

  const isEmpty = messages.length === 0

  return (
    <div className="relative flex h-screen flex-col bg-background">
      <input ref={fileInputRef} type="file" accept="application/pdf" className="hidden"
        aria-label="Upload PDF file" onChange={(e) => acceptFile(e.target.files?.[0])} />

      <header className="flex h-14 shrink-0 items-center justify-between px-4 md:px-6">
        <span className="hidden text-sm text-muted-foreground sm:inline">PaperTrail</span>
        {!isEmpty && (
          <button onClick={startNewChat}
            className="flex items-center gap-1.5 rounded-full border border-border px-3 py-1.5 text-xs font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground">
            <Plus /> New chat
          </button>
        )}
      </header>

      {/* Messages */}
      <div className="thin-scroll flex-1 overflow-y-auto">
        <div className="mx-auto w-full max-w-3xl px-4 md:px-6">
          {isEmpty ? (
            <div className="flex min-h-[calc(100vh-16rem)] flex-col items-center justify-center text-center">
              <div className="mb-6 flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/15 text-primary ring-1 ring-primary/25">
                <Brain className="h-7 w-7" />
              </div>
              <h1 className="text-[2rem] font-bold tracking-tight">
                Welcome to <span className="text-primary">PaperTrail</span>
              </h1>
              <p className="mt-3 max-w-md text-[0.975rem] text-muted-foreground">
                Ask about your indexed papers — I&apos;ll search them and cite what I find.
              </p>
              <div className="mt-8 grid w-full max-w-lg grid-cols-1 gap-2 sm:grid-cols-2">
                {SUGGESTIONS.map((s) => (
                  <button key={s} onClick={() => setInput(s)}
                    className="group rounded-xl border border-border bg-card/40 px-4 py-3 text-left text-sm text-muted-foreground transition-all hover:border-primary/40 hover:bg-card hover:text-foreground">
                    <span className="mr-2 text-primary">→</span>{s}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="space-y-7 py-8">
              {messages.map((m) => {
                const text = textOf(m)
                if (m.role === 'user') {
                  return (
                    <div key={m.id} className="flex justify-end animate-in fade-in slide-in-from-bottom-2 duration-300">
                      <div className="max-w-[80%] rounded-2xl rounded-br-md bg-secondary px-4 py-2.5 text-[0.95rem] leading-relaxed">
                        {text}
                      </div>
                    </div>
                  )
                }
                const parts = m.parts ?? []
                const tools = parts.filter(
                  (p: any): p is ToolPartLike =>
                    typeof p?.type === 'string' && p.type.startsWith('tool-')
                )
                const lastStreamingPart =
                  status === 'streaming' && m.id === messages[messages.length - 1]?.id
                const reasoningText = reasoningOf(m)
                const isLastAssistant = m.id === messages[messages.length - 1]?.id && m.role === 'assistant'

                return (
                  <div key={m.id} className="group animate-in fade-in slide-in-from-bottom-2 duration-300">
                    {reasoningText && (
                      <ThinkingBlock text={reasoningText} streaming={lastStreamingPart && !text} />
                    )}
                    {tools.map((t, i) => <ToolChip key={i} part={t} />)}
                    {text && (
                      <div className="chat-markdown">
                        <ReactMarkdown remarkPlugins={[remarkGfm, remarkMath]} rehypePlugins={[rehypeKatex]}>
                          {text}
                        </ReactMarkdown>
                      </div>
                    )}
                    {text && !isBusy && (
                      <div className="mt-2 flex items-center gap-0.5 opacity-0 transition-opacity group-hover:opacity-100">
                        <button onClick={() => copyMessage(m.id, text)} title="Copy"
                          className="flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground">
                          {copiedId === m.id ? <Check className="h-4 w-4 text-success" /> : <Copy className="h-4 w-4" />}
                        </button>
                        {isLastAssistant && (
                          <button onClick={() => regenerate()} title="Regenerate"
                            className="flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground">
                            <RefreshCw className="h-4 w-4" />
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                )
              })}

              {status === 'submitted' && (
                <div className="flex items-center gap-1.5">
                  {[0, 150, 300].map((d) => (
                    <span key={d} className="h-2 w-2 animate-bounce rounded-full bg-primary/70"
                      style={{ animationDelay: `${d}ms` } as React.CSSProperties} />
                  ))}
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>
      </div>

      {/* Composer */}
      <div className="shrink-0 px-4 pb-5 md:px-6 md:pb-6">
        <div className="mx-auto w-full max-w-3xl">
          {(selectedFile || uploadStatus !== 'idle' || uploadError) && (
            <div className={cn('glass mb-3 rounded-2xl border p-4',
              uploadStatus === 'success' ? 'border-success/40' : uploadStatus === 'error' ? 'border-destructive/40' : 'border-border')}>
              <div className="flex items-center justify-between gap-3">
                <div className="flex min-w-0 flex-1 items-center gap-3 text-sm">
                  {uploadStatus === 'success' ? <CheckCircle2 className="h-5 w-5 shrink-0 text-success" />
                    : uploadStatus === 'uploading' ? <Loader2 className="h-5 w-5 shrink-0 animate-spin text-primary" />
                    : <FileText className="h-5 w-5 shrink-0 text-primary" />}
                  <span className="block truncate font-medium">{selectedFile?.name ?? 'No file'}</span>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  {selectedFile && uploadStatus === 'idle' && (
                    <button onClick={handleUpload}
                      className="flex items-center gap-1.5 rounded-full bg-primary px-3.5 py-1.5 text-xs font-semibold text-primary-foreground hover:opacity-90">
                      <ArrowUp className="h-3.5 w-3.5" /> Index paper
                    </button>
                  )}
                  <button onClick={resetUpload} className="rounded-full p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground">
                    <X className="h-4 w-4" />
                  </button>
                </div>
              </div>
              {uploadProgress > 0 && (
                <div className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-muted">
                  <div className="h-full rounded-full bg-primary transition-all duration-500" style={{ width: `${uploadProgress}%` }} />
                </div>
              )}
              {processingMessage && <p className="mt-3 text-sm text-muted-foreground">{processingMessage}</p>}
              {uploadError && <p className="mt-3 text-sm font-medium text-destructive">{uploadError}</p>}
            </div>
          )}

          {error && (
            <div className="glass mb-3 flex items-center justify-between gap-3 rounded-2xl border border-destructive/40 p-3">
              <p className="text-sm text-destructive">{error.message}</p>
              <button onClick={() => startNewChat()}
                className="flex items-center gap-1.5 rounded-full bg-primary px-3 py-1.5 text-xs font-semibold text-primary-foreground hover:opacity-90">
                <RefreshCw className="h-3.5 w-3.5" /> New chat
              </button>
            </div>
          )}

          <form ref={formRef} onSubmit={onSubmit} {...getRootProps()}
            className={cn('glass rounded-2xl border shadow-2xl shadow-black/20 transition-colors',
              isDragActive ? 'border-primary ring-2 ring-primary/30' : 'border-border')}>
            <input {...getInputProps()} />
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={isDragActive ? 'Drop your PDF to index it…' : 'Ask about your research papers…'}
              rows={1}
              className="max-h-[220px] w-full resize-none bg-transparent px-4 pt-4 text-[0.975rem] leading-relaxed placeholder:text-muted-foreground focus:outline-none"
            />

            <div className="flex items-center justify-between gap-2 px-3 pb-3 pt-1">
              <div className="relative flex items-center gap-1.5">
                {/* Model picker */}
                <button type="button" onClick={() => setModelOpen((v) => !v)}
                  className="flex items-center gap-1.5 rounded-full px-2.5 py-1.5 text-xs font-medium text-foreground transition-colors hover:bg-muted">
                  <span className="h-1.5 w-1.5 rounded-full bg-primary" />
                  {activeModel.label}
                  <ChevronDown className={cn('h-3.5 w-3.5 text-muted-foreground transition-transform', modelOpen && 'rotate-180')} />
                </button>
                {modelOpen && (
                  <>
                    <div className="fixed inset-0 z-40" onClick={() => setModelOpen(false)} />
                    <div className="absolute bottom-full left-0 z-50 mb-2 w-72 overflow-hidden rounded-xl border border-border bg-popover shadow-2xl shadow-black/40">
                      {CHAT_MODELS.map((m) => (
                        <button key={m.id} type="button"
                          onClick={() => { setModelId(m.id); setModelOpen(false) }}
                          className={cn('flex w-full items-start justify-between gap-2 px-3 py-2.5 text-left transition-colors hover:bg-muted',
                            m.id === modelId && 'bg-primary/10')}>
                          <span>
                            <span className={cn('block text-sm font-medium', m.id === modelId && 'text-primary')}>{m.label}</span>
                            <span className="block text-xs text-muted-foreground">{m.hint}</span>
                          </span>
                          {m.id === modelId && <Check className="mt-0.5 h-4 w-4 shrink-0 text-primary" />}
                        </button>
                      ))}
                    </div>
                  </>
                )}
                <button type="button" onClick={() => fileInputRef.current?.click()} title="Attach a PDF"
                  className="flex items-center gap-1.5 rounded-full border border-border px-2.5 py-1.5 text-xs font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground">
                  <Paperclip className="h-3.5 w-3.5" />
                  <span className="hidden sm:inline">Attach</span>
                </button>
              </div>

              {isBusy ? (
                <button type="button" onClick={stop} aria-label="Stop"
                  className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-primary-foreground hover:opacity-90">
                  <Square className="h-3.5 w-3.5 fill-current" />
                </button>
              ) : (
                <button type="submit" disabled={!input.trim()} aria-label="Send message"
                  className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-primary-foreground transition-all hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-30">
                  <ArrowUp className="h-4 w-4" />
                </button>
              )}
            </div>
          </form>

          <p className="mt-2.5 text-center text-xs text-muted-foreground/70">
            Enter to send · Shift+Enter for a new line · drag a PDF to index it
          </p>
        </div>
      </div>
    </div>
  )
}
