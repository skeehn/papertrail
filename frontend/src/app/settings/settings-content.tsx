"use client"

import React, { useCallback, useEffect, useState } from 'react'
import { Check, Eye, EyeOff, Loader2, RefreshCw, Save } from 'lucide-react'
import { cn } from '@/lib/utils'

interface KeyState {
  configured: boolean
  value: string
}

interface ServiceState {
  configured: boolean
  required: boolean
  label: string
  unlocks: string
}

interface StatusResponse {
  services: Record<string, ServiceState>
  keys: Record<string, KeyState>
}

/** Secrets are never returned by the API — only whether they are set. */
const SECRET_FIELDS = new Set(['OPENAI_API_KEY', 'PINECONE_API_KEY', 'NEO4J_PASSWORD'])

const GROUPS: {
  title: string
  blurb: string
  required?: boolean
  fields: { key: string; label: string; placeholder: string }[]
}[] = [
  {
    title: 'Chat model',
    blurb: 'Required. Add a key here and the chat works — nothing else is needed.',
    required: true,
    fields: [
      { key: 'OPENAI_API_KEY', label: 'API key', placeholder: 'sk-or-v1-…' },
      {
        key: 'OPENAI_BASE_URL',
        label: 'Base URL',
        placeholder: 'https://openrouter.ai/api/v1',
      },
      {
        key: 'OPENAI_MODEL',
        label: 'Default model',
        placeholder: 'nvidia/nemotron-3-ultra-550b-a55b:free',
      },
    ],
  },
  {
    title: 'Pinecone',
    blurb:
      'Optional. Enables semantic search over your papers; without it, search falls back to keywords.',
    fields: [
      { key: 'PINECONE_API_KEY', label: 'API key', placeholder: 'pcsk_…' },
      { key: 'PINECONE_INDEX_NAME', label: 'Index name', placeholder: 'papertrail' },
      { key: 'PINECONE_HOST', label: 'Host', placeholder: 'papertrail-xxx.svc.pinecone.io' },
    ],
  },
  {
    title: 'Neo4j',
    blurb:
      'Optional. Stores the paper library and knowledge graph; without it the graph stays empty.',
    fields: [
      { key: 'NEO4J_URI', label: 'URI', placeholder: 'neo4j+s://xxxx.databases.neo4j.io' },
      { key: 'NEO4J_USERNAME', label: 'Username', placeholder: 'neo4j' },
      { key: 'NEO4J_PASSWORD', label: 'Password', placeholder: '••••••••' },
    ],
  },
]

export default function SettingsContent() {
  const [status, setStatus] = useState<StatusResponse | null>(null)
  const [values, setValues] = useState<Record<string, string>>({})
  const [reveal, setReveal] = useState<Record<string, boolean>>({})
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch('/api/settings/keys', { cache: 'no-store' })
      if (!res.ok) throw new Error('Could not reach the backend')
      const data: StatusResponse = await res.json()
      setStatus(data)
      // Prefill non-secret fields with their current values
      const next: Record<string, string> = {}
      Object.entries(data.keys || {}).forEach(([k, v]) => {
        if (!SECRET_FIELDS.has(k)) next[k] = v.value || ''
      })
      setValues(next)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const save = async () => {
    setSaving(true)
    setError(null)
    try {
      // Only send fields with a value; blank secrets mean "keep what's saved"
      const payload: Record<string, string> = {}
      Object.entries(values).forEach(([k, v]) => {
        if (v !== '') payload[k] = v
      })
      const res = await fetch('/api/settings/keys', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (!res.ok) throw new Error('Save failed')
      const data = await res.json()
      setStatus({ services: data.services, keys: data.keys })
      // Drop secret inputs from memory once saved
      setValues((prev) => {
        const next = { ...prev }
        SECRET_FIELDS.forEach((k) => delete next[k])
        return next
      })
      setSaved(true)
      setTimeout(() => setSaved(false), 2500)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-8 pb-12">
      <section>
        <h2 className="mb-1 text-lg font-semibold">Status</h2>
        <p className="mb-4 text-sm text-muted-foreground">
          Only the chat model is required. Everything else adds features.
        </p>
        <div className="grid gap-3 sm:grid-cols-3">
          {loading && !status ? (
            <div className="col-span-full flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" /> Checking services…
            </div>
          ) : (
            Object.entries(status?.services ?? {}).map(([id, s]) => (
              <div key={id} className="rounded-xl border border-border bg-card/40 p-4">
                <div className="flex items-center gap-2">
                  <span
                    className={cn(
                      'h-2 w-2 rounded-full',
                      s.configured
                        ? 'bg-success'
                        : s.required
                          ? 'bg-destructive'
                          : 'bg-muted-foreground/50'
                    )}
                  />
                  <span className="text-sm font-medium">{s.label}</span>
                  <span className="ml-auto text-xs text-muted-foreground">
                    {s.configured ? 'connected' : s.required ? 'required' : 'optional'}
                  </span>
                </div>
                <p className="mt-2 text-xs leading-relaxed text-muted-foreground">
                  {s.unlocks}
                </p>
              </div>
            ))
          )}
        </div>
      </section>

      <section className="space-y-6">
        <div>
          <h2 className="mb-1 text-lg font-semibold">API keys</h2>
          <p className="text-sm text-muted-foreground">
            Saved to{' '}
            <code className="rounded bg-muted px-1 py-0.5 text-xs">
              ~/.papertrail/config.json
            </code>{' '}
            on this machine (permissions 600). Never committed, never sent to the browser.
          </p>
        </div>

        {GROUPS.map((group) => (
          <div key={group.title} className="rounded-xl border border-border bg-card/40 p-5">
            <div className="mb-1 flex items-center gap-2">
              <h3 className="text-sm font-semibold">{group.title}</h3>
              <span
                className={cn(
                  'rounded-full px-2 py-0.5 text-[10px] font-medium',
                  group.required
                    ? 'bg-primary/15 text-primary'
                    : 'bg-muted text-muted-foreground'
                )}
              >
                {group.required ? 'required' : 'optional'}
              </span>
            </div>
            <p className="mb-4 text-xs text-muted-foreground">{group.blurb}</p>
            <div className="space-y-3">
              {group.fields.map((f) => {
                const isSecret = SECRET_FIELDS.has(f.key)
                const configured = status?.keys?.[f.key]?.configured
                return (
                  <div key={f.key}>
                    <label
                      htmlFor={f.key}
                      className="mb-1 flex items-center gap-2 text-xs text-muted-foreground"
                    >
                      {f.label}
                      {isSecret && configured && (
                        <span className="flex items-center gap-1 text-success">
                          <Check className="h-3 w-3" /> saved
                        </span>
                      )}
                    </label>
                    <div className="relative">
                      <input
                        id={f.key}
                        type={isSecret && !reveal[f.key] ? 'password' : 'text'}
                        value={values[f.key] ?? ''}
                        onChange={(e) =>
                          setValues((p) => ({ ...p, [f.key]: e.target.value }))
                        }
                        placeholder={
                          isSecret && configured
                            ? '•••••••• (leave blank to keep)'
                            : f.placeholder
                        }
                        className="w-full rounded-lg border border-border bg-background px-3 py-2 pr-10 text-sm outline-none transition-colors focus:border-primary/60"
                      />
                      {isSecret && (
                        <button
                          type="button"
                          aria-label={reveal[f.key] ? 'Hide' : 'Show'}
                          onClick={() =>
                            setReveal((p) => ({ ...p, [f.key]: !p[f.key] }))
                          }
                          className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-muted-foreground hover:text-foreground"
                        >
                          {reveal[f.key] ? (
                            <EyeOff className="h-4 w-4" />
                          ) : (
                            <Eye className="h-4 w-4" />
                          )}
                        </button>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        ))}

        {error && (
          <p className="rounded-lg border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
            {error}
          </p>
        )}

        <div className="flex items-center gap-3">
          <button
            onClick={save}
            disabled={saving}
            className="flex items-center gap-2 rounded-full bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground transition-opacity hover:opacity-90 disabled:opacity-50"
          >
            {saving ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : saved ? (
              <Check className="h-4 w-4" />
            ) : (
              <Save className="h-4 w-4" />
            )}
            {saving ? 'Saving…' : saved ? 'Saved' : 'Save keys'}
          </button>
          <button
            onClick={load}
            className="flex items-center gap-2 rounded-full border border-border px-4 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
          >
            <RefreshCw className="h-4 w-4" /> Recheck
          </button>
        </div>
      </section>
    </div>
  )
}
