"use client"

import React from 'react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'
import { useTheme } from 'next-themes'
import { Moon, Sun, Monitor } from 'lucide-react'
import { cn } from '@/lib/utils'

export default function SettingsContent() {
  const { theme, setTheme } = useTheme()

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Appearance */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-4">Appearance</h3>

        <div className="space-y-4">
          <div>
            <Label className="text-sm font-medium mb-3 block">Theme</Label>
            <div className="grid grid-cols-3 gap-3">
              <button
                onClick={() => setTheme('light')}
                className={cn(
                  'flex flex-col items-center gap-2 p-4 border-2 rounded-lg transition-all',
                  theme === 'light' ? 'border-primary-600 bg-primary-50' : 'border-border hover:border-muted-foreground/50'
                )}
              >
                <Sun className="w-5 h-5" />
                <span className="text-sm font-medium">Light</span>
              </button>
              <button
                onClick={() => setTheme('dark')}
                className={cn(
                  'flex flex-col items-center gap-2 p-4 border-2 rounded-lg transition-all',
                  theme === 'dark' ? 'border-primary-600 bg-primary-50' : 'border-border hover:border-muted-foreground/50'
                )}
              >
                <Moon className="w-5 h-5" />
                <span className="text-sm font-medium">Dark</span>
              </button>
              <button
                onClick={() => setTheme('system')}
                className={cn(
                  'flex flex-col items-center gap-2 p-4 border-2 rounded-lg transition-all',
                  theme === 'system' ? 'border-primary-600 bg-primary-50' : 'border-border hover:border-muted-foreground/50'
                )}
              >
                <Monitor className="w-5 h-5" />
                <span className="text-sm font-medium">System</span>
              </button>
            </div>
          </div>

          <div className="flex items-center justify-between">
            <div>
              <Label htmlFor="compact-mode">Compact mode</Label>
              <p className="text-xs text-muted-foreground">Reduce spacing and padding</p>
            </div>
            <Switch id="compact-mode" />
          </div>

          <div className="flex items-center justify-between">
            <div>
              <Label htmlFor="animations">Animations</Label>
              <p className="text-xs text-muted-foreground">Enable UI animations</p>
            </div>
            <Switch id="animations" defaultChecked />
          </div>
        </div>
      </Card>

      {/* Chat Settings */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-4">Chat</h3>

        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <Label htmlFor="streaming">Stream responses</Label>
              <p className="text-xs text-muted-foreground">Show AI responses as they&apos;re generated</p>
            </div>
            <Switch id="streaming" defaultChecked />
          </div>

          <div className="flex items-center justify-between">
            <div>
              <Label htmlFor="code-highlighting">Code syntax highlighting</Label>
              <p className="text-xs text-muted-foreground">Highlight code in responses</p>
            </div>
            <Switch id="code-highlighting" defaultChecked />
          </div>

          <div className="flex items-center justify-between">
            <div>
              <Label htmlFor="markdown">Markdown rendering</Label>
              <p className="text-xs text-muted-foreground">Render formatted text</p>
            </div>
            <Switch id="markdown" defaultChecked />
          </div>
        </div>
      </Card>

      {/* Papers */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-4">Papers</h3>

        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <Label htmlFor="auto-process">Auto-process uploads</Label>
              <p className="text-xs text-muted-foreground">Automatically extract claims and metadata</p>
            </div>
            <Switch id="auto-process" defaultChecked />
          </div>

          <div>
            <Label htmlFor="default-view">Default view</Label>
            <select
              id="default-view"
              className="mt-2 w-full px-3 py-2 border rounded-lg bg-background"
            >
              <option value="grid">Grid</option>
              <option value="list">List</option>
            </select>
          </div>
        </div>
      </Card>

      {/* Notifications */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-4">Notifications</h3>

        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <Label htmlFor="processing-complete">Paper processing complete</Label>
              <p className="text-xs text-muted-foreground">When a paper finishes processing</p>
            </div>
            <Switch id="processing-complete" defaultChecked />
          </div>

          <div className="flex items-center justify-between">
            <div>
              <Label htmlFor="new-insights">New insights discovered</Label>
              <p className="text-xs text-muted-foreground">When the system finds new connections</p>
            </div>
            <Switch id="new-insights" />
          </div>
        </div>
      </Card>

      {/* Account */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-4">Account</h3>

        <div className="space-y-4">
          <div>
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              placeholder="your.email@example.com"
              className="mt-2"
            />
          </div>

          <div>
            <Label htmlFor="name">Name</Label>
            <Input
              id="name"
              type="text"
              placeholder="Your Name"
              className="mt-2"
            />
          </div>

          <Button>Save Changes</Button>
        </div>
      </Card>

      {/* Danger Zone */}
      <Card className="p-6 border-destructive/50">
        <h3 className="text-lg font-semibold mb-4 text-destructive">Danger Zone</h3>

        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <Label>Clear all data</Label>
              <p className="text-xs text-muted-foreground">Delete all papers, conversations, and settings</p>
            </div>
            <Button variant="destructive" size="sm">Clear Data</Button>
          </div>

          <div className="flex items-center justify-between">
            <div>
              <Label>Delete account</Label>
              <p className="text-xs text-muted-foreground">Permanently delete your account</p>
            </div>
            <Button variant="destructive" size="sm">Delete Account</Button>
          </div>
        </div>
      </Card>
    </div>
  )
}
