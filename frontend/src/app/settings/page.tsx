"use client"

import React from 'react'
import { AppLayout, PageHeader, PageContent } from '@/components/layout/app-layout'
import { Card } from '@/components/ui/card'
import { Palette, Bell, Shield, User, Zap } from 'lucide-react'

export default function SettingsPage() {
  const settingsSections = [
    {
      title: 'Appearance',
      description: 'Customize the look and feel',
      icon: Palette,
      color: 'from-purple-500/10 to-purple-600/10 text-purple-600',
    },
    {
      title: 'Notifications',
      description: 'Manage notification preferences',
      icon: Bell,
      color: 'from-blue-500/10 to-blue-600/10 text-blue-600',
    },
    {
      title: 'Privacy & Security',
      description: 'Control your data and privacy settings',
      icon: Shield,
      color: 'from-green-500/10 to-green-600/10 text-green-600',
    },
    {
      title: 'Account',
      description: 'Manage your account details',
      icon: User,
      color: 'from-orange-500/10 to-orange-600/10 text-orange-600',
    },
    {
      title: 'Integrations',
      description: 'Connect external services',
      icon: Zap,
      color: 'from-yellow-500/10 to-yellow-600/10 text-yellow-600',
    },
  ]

  return (
    <AppLayout>
      <PageHeader
        title="Settings"
        description="Manage your preferences and account settings"
      />
      <PageContent maxWidth="4xl">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {settingsSections.map((section) => {
            const Icon = section.icon
            return (
              <Card
                key={section.title}
                className="p-6 hover:shadow-md transition-all duration-200 cursor-pointer group"
              >
                <div className="flex items-start gap-4">
                  <div className={`p-3 rounded-lg bg-gradient-to-br ${section.color} group-hover:scale-110 transition-transform`}>
                    <Icon className="w-6 h-6" />
                  </div>
                  <div>
                    <h3 className="font-semibold mb-1">{section.title}</h3>
                    <p className="text-sm text-muted-foreground">
                      {section.description}
                    </p>
                  </div>
                </div>
              </Card>
            )
          })}
        </div>
      </PageContent>
    </AppLayout>
  )
}
