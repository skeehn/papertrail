"use client"

import React from 'react'
import { AppLayout, PageHeader, PageContent } from '@/components/layout/app-layout'
import { StatsCard } from '@/components/dashboard/stats-card'
import { ActivityFeed } from '@/components/dashboard/activity-feed'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import {
  FileText,
  MessageSquare,
  Lightbulb,
  Network,
  Plus,
  Upload,
  Search,
  TrendingUp,
} from 'lucide-react'
import Link from 'next/link'

// Mock data - replace with real data from API
const mockStats = {
  totalPapers: 24,
  activeConversations: 8,
  claimsExtracted: 156,
  graphNodes: 342,
}

const mockActivities = [
  {
    id: '1',
    type: 'paper_uploaded' as const,
    title: 'New paper uploaded',
    description: 'Attention Is All You Need.pdf',
    timestamp: new Date(Date.now() - 1000 * 60 * 15), // 15 minutes ago
  },
  {
    id: '2',
    type: 'conversation_started' as const,
    title: 'Started new conversation',
    description: 'Discussing transformer architecture and attention mechanisms',
    timestamp: new Date(Date.now() - 1000 * 60 * 60 * 2), // 2 hours ago
  },
  {
    id: '3',
    type: 'claim_extracted' as const,
    title: '12 claims extracted',
    description: 'From "Deep Learning for Computer Vision"',
    timestamp: new Date(Date.now() - 1000 * 60 * 60 * 5), // 5 hours ago
  },
  {
    id: '4',
    type: 'graph_updated' as const,
    title: 'Knowledge graph updated',
    description: 'Added 23 new relationships between papers',
    timestamp: new Date(Date.now() - 1000 * 60 * 60 * 24), // 1 day ago
  },
  {
    id: '5',
    type: 'paper_processed' as const,
    title: 'Paper processing complete',
    description: 'Neural Networks and Deep Learning.pdf',
    timestamp: new Date(Date.now() - 1000 * 60 * 60 * 48), // 2 days ago
  },
]

export default function DashboardPage() {
  return (
    <AppLayout>
      <PageHeader
        title="Dashboard"
        description="Welcome back! Here's an overview of your research activity."
        actions={
          <Button asChild>
            <Link href="/">
              <MessageSquare className="w-4 h-4 mr-2" />
              New Chat
            </Link>
          </Button>
        }
      />
      <PageContent maxWidth="6xl">
        <div className="space-y-6">
          {/* Stats Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <StatsCard
              title="Total Papers"
              value={mockStats.totalPapers}
              icon={FileText}
              trend={{ value: 12, isPositive: true }}
            />
            <StatsCard
              title="Conversations"
              value={mockStats.activeConversations}
              icon={MessageSquare}
              trend={{ value: 8, isPositive: true }}
            />
            <StatsCard
              title="Claims Extracted"
              value={mockStats.claimsExtracted}
              icon={Lightbulb}
              trend={{ value: 24, isPositive: true }}
            />
            <StatsCard
              title="Graph Nodes"
              value={mockStats.graphNodes}
              icon={Network}
              trend={{ value: 15, isPositive: true }}
            />
          </div>

          {/* Quick Actions */}
          <div>
            <h2 className="text-lg font-semibold mb-3">Quick Actions</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
              <Card className="p-4 hover:shadow-md transition-all duration-200 cursor-pointer group">
                <Link href="/" className="flex items-start gap-3">
                  <div className="p-2 rounded-lg bg-gradient-to-br from-blue-500/10 to-blue-600/10 group-hover:from-blue-500/20 group-hover:to-blue-600/20 transition-colors">
                    <Plus className="w-5 h-5 text-blue-600" />
                  </div>
                  <div>
                    <h3 className="font-medium text-sm">New Conversation</h3>
                    <p className="text-xs text-muted-foreground mt-1">
                      Start chatting with AI
                    </p>
                  </div>
                </Link>
              </Card>

              <Card className="p-4 hover:shadow-md transition-all duration-200 cursor-pointer group">
                <Link href="/" className="flex items-start gap-3">
                  <div className="p-2 rounded-lg bg-gradient-to-br from-green-500/10 to-green-600/10 group-hover:from-green-500/20 group-hover:to-green-600/20 transition-colors">
                    <Upload className="w-5 h-5 text-green-600" />
                  </div>
                  <div>
                    <h3 className="font-medium text-sm">Upload Paper</h3>
                    <p className="text-xs text-muted-foreground mt-1">
                      Add new research paper
                    </p>
                  </div>
                </Link>
              </Card>

              <Card className="p-4 hover:shadow-md transition-all duration-200 cursor-pointer group">
                <Link href="/graph" className="flex items-start gap-3">
                  <div className="p-2 rounded-lg bg-gradient-to-br from-purple-500/10 to-purple-600/10 group-hover:from-purple-500/20 group-hover:to-purple-600/20 transition-colors">
                    <Search className="w-5 h-5 text-purple-600" />
                  </div>
                  <div>
                    <h3 className="font-medium text-sm">Explore Graph</h3>
                    <p className="text-xs text-muted-foreground mt-1">
                      Visualize connections
                    </p>
                  </div>
                </Link>
              </Card>

              <Card className="p-4 hover:shadow-md transition-all duration-200 cursor-pointer group">
                <Link href="/papers" className="flex items-start gap-3">
                  <div className="p-2 rounded-lg bg-gradient-to-br from-orange-500/10 to-orange-600/10 group-hover:from-orange-500/20 group-hover:to-orange-600/20 transition-colors">
                    <FileText className="w-5 h-5 text-orange-600" />
                  </div>
                  <div>
                    <h3 className="font-medium text-sm">View Papers</h3>
                    <p className="text-xs text-muted-foreground mt-1">
                      Browse your library
                    </p>
                  </div>
                </Link>
              </Card>
            </div>
          </div>

          {/* Main Content Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Activity Feed */}
            <div className="lg:col-span-2">
              <ActivityFeed activities={mockActivities} />
            </div>

            {/* Insights Sidebar */}
            <div className="space-y-4">
              <Card className="p-6">
                <div className="flex items-center gap-2 mb-4">
                  <TrendingUp className="w-5 h-5 text-primary-600" />
                  <h3 className="text-lg font-semibold">Top Topics</h3>
                </div>
                <div className="space-y-3">
                  {[
                    { topic: 'Deep Learning', count: 12 },
                    { topic: 'Neural Networks', count: 9 },
                    { topic: 'Computer Vision', count: 7 },
                    { topic: 'NLP', count: 6 },
                    { topic: 'Transformers', count: 5 },
                  ].map((item) => (
                    <div key={item.topic} className="flex items-center justify-between">
                      <span className="text-sm">{item.topic}</span>
                      <span className="text-xs bg-muted px-2 py-1 rounded-full">
                        {item.count} papers
                      </span>
                    </div>
                  ))}
                </div>
              </Card>

              <Card className="p-6">
                <h3 className="text-lg font-semibold mb-4">Recent Insights</h3>
                <div className="space-y-3">
                  <div className="text-sm">
                    <p className="font-medium">Emerging Pattern</p>
                    <p className="text-xs text-muted-foreground mt-1">
                      5 papers discuss attention mechanisms in transformers
                    </p>
                  </div>
                  <div className="text-sm">
                    <p className="font-medium">Research Gap</p>
                    <p className="text-xs text-muted-foreground mt-1">
                      Limited coverage of multi-modal learning approaches
                    </p>
                  </div>
                </div>
              </Card>
            </div>
          </div>
        </div>
      </PageContent>
    </AppLayout>
  )
}
