/**
 * Multi-conversation store.
 *
 * localStorage-backed CRUD for chats. One storage key per conversation plus a
 * lightweight index document so the sidebar can render instantly without
 * loading every thread's messages.
 *
 * Cross-tab sync: writes dispatch a `papertrail:conversations` window event and
 * also listen to the browser's native `storage` event, so the sidebar and the
 * chat surface stay in sync whether the other tab wrote via the store API or
 * directly to localStorage.
 */

import type { UIMessage } from 'ai'

export interface StoredConversationMeta {
  id: string
  title: string
  createdAt: number
  updatedAt: number
  messageCount: number
  modelId?: string
  pinned?: boolean
}

interface ConversationPayload {
  meta: StoredConversationMeta
  messages: UIMessage[]
}

const INDEX_KEY = 'papertrail_conversations_index'
const CONV_KEY_PREFIX = 'papertrail_conversation_'
export const CONVERSATIONS_EVENT = 'papertrail:conversations'

/** Listeners for store lifecycle (same-tab subscribers). */
const listeners = new Set<() => void>()

function conversationKey(id: string): string {
  return CONV_KEY_PREFIX + id
}

function safeParse<T>(raw: string | null, fallback: T): T {
  if (!raw) return fallback
  try {
    const parsed = JSON.parse(raw)
    return parsed ?? fallback
  } catch {
    return fallback
  }
}

function storage(): Storage | null {
  if (typeof window === 'undefined') return null
  try {
    return window.localStorage ?? null
  } catch {
    return null
  }
}

function readIndex(): StoredConversationMeta[] {
  const store = storage()
  if (!store) return []
  return safeParse<StoredConversationMeta[]>(store.getItem(INDEX_KEY), [])
}

function writeIndex(index: StoredConversationMeta[]): void {
  storage()?.setItem(INDEX_KEY, JSON.stringify(index))
  notify()
}

function notify(): void {
  window.dispatchEvent(new CustomEvent(CONVERSATIONS_EVENT))
  for (const fn of listeners) fn()
}

function metaOf(messages: UIMessage[]): Pick<
  StoredConversationMeta,
  'title' | 'messageCount'
> {
  const firstUser = messages.find((m) => m.role === 'user')
  const firstText =
    (firstUser?.parts as Array<{ type: string; text?: string }> | undefined)
      ?.filter((p) => p.type === 'text')
      .map((p) => p.text ?? '')
      .join(' ') ?? ''
  const title = firstText.trim()
    ? firstText.trim().slice(0, 60)
    : 'New chat'
  return { title, messageCount: messages.length }
}

export const conversationStore = {
  /** All conversation metadata, newest first. */
  list(): StoredConversationMeta[] {
    return readIndex().sort((a, b) => b.updatedAt - a.updatedAt)
  },

  /** Load one conversation's full messages. Returns [] when absent. */
  load(id: string): UIMessage[] {
    if (typeof window === 'undefined') return []
    const store = storage()
    if (!store) return []
    const payload = safeParse<ConversationPayload | null>(
      store.getItem(conversationKey(id)),
      null
    )
    return Array.isArray(payload?.messages) ? payload.messages : []
  },

  /** Persist messages for a conversation, upserting its index entry. */
  save(
    id: string,
    messages: UIMessage[],
    opts: { modelId?: string; pinned?: boolean } = {}
  ): void {
    if (typeof window === 'undefined') return
    const existing = readIndex().find((c) => c.id === id)
    const meta: StoredConversationMeta = {
      id,
      title: metaOf(messages).title,
      createdAt: existing?.createdAt ?? Date.now(),
      updatedAt: Date.now(),
      messageCount: messages.length,
      modelId: opts.modelId ?? existing?.modelId,
      pinned: opts.pinned ?? existing?.pinned,
    }
    const store = storage()
    if (!store) return
    const payload: ConversationPayload = { meta, messages }
    store.setItem(conversationKey(id), JSON.stringify(payload))

    const index = readIndex().filter((c) => c.id !== id)
    index.push(meta)
    writeIndex(index)
  },

  rename(id: string, title: string): void {
    const index = readIndex()
    const entry = index.find((c) => c.id === id)
    if (!entry) return
    entry.title = title.trim() || entry.title
    writeIndex(index)

    // Keep the payload's embedded meta consistent.
    const raw = storage()?.getItem(conversationKey(id)) ?? null
    if (raw) {
      const payload = safeParse<ConversationPayload | null>(raw, null)
      if (payload) {
        payload.meta.title = entry.title
        storage()?.setItem(conversationKey(id), JSON.stringify(payload))
      }
    }
  },

  togglePinned(id: string): void {
    const index = readIndex()
    const entry = index.find((c) => c.id === id)
    if (!entry) return
    entry.pinned = !entry.pinned
    writeIndex(index)
  },

  /** Remove a conversation and its messages. Returns true if it existed. */
  remove(id: string): boolean {
    const index = readIndex()
    const had = index.some((c) => c.id === id)
    storage()?.removeItem(conversationKey(id))
    writeIndex(index.filter((c) => c.id !== id))
    return had
  },

  /** Subscribe to same-tab updates (cross-tab arrives via `storage`). */
  subscribe(fn: () => void): () => void {
    listeners.add(fn)
    return () => listeners.delete(fn)
  },
}

/** Auto id for a new conversation. */
export function newConversationId(): string {
  return `conv_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 9)}`
}
