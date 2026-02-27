import '@testing-library/jest-dom'
import { vi } from 'vitest'

// Mock Next.js router
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    prefetch: vi.fn(),
  }),
  usePathname: () => '/',
  useSearchParams: () => new URLSearchParams(),
}))

// Mock WebSocket
global.WebSocket = class WebSocket {
  constructor() {}
  addEventListener() {}
  removeEventListener() {}
  send() {}
  close() {}
} as any

// Mock ResizeObserver (not available in jsdom)
global.ResizeObserver = class ResizeObserver {
  constructor(_callback: ResizeObserverCallback) {}
  observe() {}
  unobserve() {}
  disconnect() {}
}

// Mock scrollIntoView (not implemented in jsdom)
Element.prototype.scrollIntoView = vi.fn()
