/**
 * Server-only config reader.
 *
 * Resolves API keys the same way the backend does: the user config file written
 * by the Settings page (~/.papertrail/config.json) wins, then environment
 * variables. Both processes read the same file, so a key saved in Settings
 * reaches the chat without a restart — and without ever sending a secret over
 * HTTP to the browser.
 *
 * Never import this from a client component.
 */

import { readFileSync } from 'fs'
import { homedir } from 'os'
import { join } from 'path'

const CONFIG_PATH = join(
  process.env.PAPERTRAIL_CONFIG_DIR || join(homedir(), '.papertrail'),
  'config.json'
)

/** Re-read per call: the file changes when the user saves Settings. */
function readUserConfig(): Record<string, string> {
  try {
    const raw = readFileSync(CONFIG_PATH, 'utf8')
    const parsed = JSON.parse(raw)
    return parsed && typeof parsed === 'object' ? parsed : {}
  } catch {
    return {} // no file yet (fresh clone) — fall back to env
  }
}

export function getKey(name: string, fallback = ''): string {
  const fromFile = readUserConfig()[name]
  if (fromFile) return fromFile
  return process.env[name] || fallback
}

export interface ProviderCreds {
  apiKey: string
  baseURL: string
}

/** Credentials for an OpenAI-compatible provider. */
export function getProviderCreds(provider: 'openrouter' | 'interfaze'): ProviderCreds {
  if (provider === 'interfaze') {
    return {
      apiKey: getKey('INTERFAZE_API_KEY'),
      baseURL: getKey('INTERFAZE_BASE_URL', 'https://api.interfaze.ai/v1'),
    }
  }
  return {
    apiKey: getKey('OPENAI_API_KEY'),
    baseURL: getKey('OPENAI_BASE_URL', 'https://openrouter.ai/api/v1'),
  }
}

/** True when a usable chat key is configured. */
export function hasLlmKey(): boolean {
  const key = getKey('OPENAI_API_KEY')
  return Boolean(key) && !key.startsWith('sk-placeholder')
}
