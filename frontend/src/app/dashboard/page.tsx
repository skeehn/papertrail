"use client"

import React, { useEffect, useState } from 'react'
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

interface DashboardStats {
  totalPapers: number
  activeConversations: number
  claimsExtracted: number
  graphNodes: number
  relationships: number
}

interface Activity {
  id: string
  type: 'paper_uploaded' | 'conversation_started' | 'claim_extracted' | 'graph_updated' | 'paper_processed'
  title: string
  description: string
  timestamp: Date
  metadata?: Record<string, any>
}

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats>({
    totalPapers: 0,
    activeConversations: 0,
    claimsExtracted: 0,
    graphNodes: 0,
    relationships: 0,
  })
  const [activities, setActivities] = useState<Activity[]>([])
  const [topTopics, setTopTopics] = useState<Array<{ topic: string; count: number }>>([])
  const [recentInsights, setRecentInsights] = useState<Array<{ title: string; description: string }>>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        // Fetch stats
        const statsResponse = await fetch('/api/dashboard/stats')
        if (!statsResponse.ok) {
          throw new Error('Failed to fetch stats')
        }
        const statsData = await statsResponse.json()
        setStats(statsData)

        // Fetch insights summary for top topics
        try {
          const insightsResponse = await fetch('/api/insights/summary')
          if (insightsResponse.ok) {
            const insightsData = await insightsResponse.json()
            // Extract top topics from trending data
            if (insightsData.trending_now && Array.isArray(insightsData.trending_now)) {
              const topics = insightsData.trending_now.slice(0, 5).map((item: any) => ({
                topic: item.entity_name || item.name || 'Unknown',
                count: item.mention_count || item.count || 0,
              }))
              setTopTopics(topics)
            }
            // Extract recent insights
            if (insightsData.emerging_topics && Array.isArray(insightsData.emerging_topics)) {
              const insights = insightsData.emerging_topics.slice(0, 2).map((item: any) => ({
                title: 'Emerging Pattern',
                description: `${item.entity_name || 'Topic'} shows ${item.growth_rate || 0}% growth`,
              }))
              setRecentInsights(insights)
            }
          }
        } catch (err) {
          console.warn('Failed to fetch insights:', err)
        }

        // Generate mock activities from papers (in real app, this would come from an audit trail)
        // For now, we'll create activities based on papers
        try {
          const papersResponse = await fetch('/api/papers/list?limit=10')
          if (papersResponse.ok) {
            const papersData = await papersResponse.ok ? await papersResponse.json() : { papers: [] }
            const papers = Array.isArray(papersData) ? papersData : (papersData.papers || [])
            const generatedActivities: Activity[] = papers.slice(0, 5).map((paper: any, index: number) => ({
              id: `activity-${paper.id || index}`,
              type: 'paper_uploaded' as const,
              title: `Paper uploaded: ${paper.title || 'Untitled'}`,
              description: `Added to library${paper.authors ? ` by ${Array.isArray(paper.authors) ? paper.authors[0] : paper.authors}` : ''}`,
              timestamp: new Date(paper.created_at || paper.uploadDate || Date.now() - index * 3600000),
              metadata: { paperId: paper.id },
            }))
            setActivities(generatedActivities)
          }
        } catch (err) {
          console.warn('Failed to fetch activities:', err)
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load dashboard')
      } finally {
        setIsLoading(false)
      }
    }

    fetchDashboardData()
  }, [])
  return (
    <AppLayout>
      <PageHeader
        title="Dashboard"
        description="Welcome back! Here's an overview of your research activity."
        actions={
          <Button asChild className="bg-foreground text-background hover:bg-foreground/90">
            <Link href="/">
              <MessageSquare className="w-4 h-4 mr-2" />
              New Chat
            </Link>
          </Button>
        }
      />
      <PageContent maxWidth="6xl">
        <div className="space-y-6">
          {error && (
            <Card className="p-4 bg-muted/30 border border-border">
              <p className="text-sm text-foreground">{error}</p>
              <Button size="sm" onClick={() => window.location.reload()} className="mt-2 bg-foreground text-background hover:bg-foreground/90">
                Retry
              </Button>
            </Card>
          )}

          {/* Stats Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <StatsCard
              title="Total Papers"
              value={stats.totalPapers}
              icon={FileText}
              trend={null}
              isLoading={isLoading}
            />
            <StatsCard
              title="Conversations"
              value={stats.activeConversations}
              icon={MessageSquare}
              trend={null}
              isLoading={isLoading}
            />
            <StatsCard
              title="Claims Extracted"
              value={stats.claimsExtracted}
              icon={Lightbulb}
              trend={null}
              isLoading={isLoading}
            />
            <StatsCard
              title="Graph Nodes"
              value={stats.graphNodes}
              icon={Network}
              trend={null}
              isLoading={isLoading}
            />
          </div>

          {/* Quick Actions */}
          <div>
            <h2 className="text-lg font-semibold mb-3">Quick Actions</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
              <Card className="p-4 hover:bg-muted/30 transition-colors cursor-pointer group border border-border/50">
                <Link href="/" className="flex items-start gap-3">
                  <div className="p-2 rounded-lg bg-muted">
                    <Plus className="w-5 h-5 text-foreground" />
                  </div>
                  <div>
                    <h3 className="font-medium text-sm">New Conversation</h3>
                    <p className="text-xs text-muted-foreground mt-1">
                      Start chatting with AI
                    </p>
                  </div>
                </Link>
              </Card>

              <Card className="p-4 hover:bg-muted/30 transition-colors cursor-pointer group border border-border/50">
                <Link href="/" className="flex items-start gap-3">
                  <div className="p-2 rounded-lg bg-muted">
                    <Upload className="w-5 h-5 text-foreground" />
                  </div>
                  <div>
                    <h3 className="font-medium text-sm">Upload Paper</h3>
                    <p className="text-xs text-muted-foreground mt-1">
                      Add new research paper
                    </p>
                  </div>
                </Link>
              </Card>

              <Card className="p-4 hover:bg-muted/30 transition-colors cursor-pointer group border border-border/50">
                <Link href="/graph" className="flex items-start gap-3">
                  <div className="p-2 rounded-lg bg-muted">
                    <Search className="w-5 h-5 text-foreground" />
                  </div>
                  <div>
                    <h3 className="font-medium text-sm">Explore Graph</h3>
                    <p className="text-xs text-muted-foreground mt-1">
                      Visualize connections
                    </p>
                  </div>
                </Link>
              </Card>

              <Card className="p-4 hover:bg-muted/30 transition-colors cursor-pointer group border border-border/50">
                <Link href="/papers" className="flex items-start gap-3">
                  <div className="p-2 rounded-lg bg-muted">
                    <FileText className="w-5 h-5 text-foreground" />
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
              <ActivityFeed activities={activities} />
            </div>

            {/* Insights Sidebar */}
            <div className="space-y-4">
              <Card className="p-6 border border-border/50">
                <div className="flex items-center gap-2 mb-4">
                  <TrendingUp className="w-5 h-5 text-foreground" />
                  <h3 className="text-lg font-semibold">Top Topics</h3>
                </div>
                <div className="space-y-3">
                  {topTopics.length > 0 ? (
                    topTopics.map((item) => (
                    <div key={item.topic} className="flex items-center justify-between">
                      <span className="text-sm">{item.topic}</span>
                      <span className="text-xs bg-muted px-2 py-1 rounded-full">
                          {item.count} mentions
                      </span>
                    </div>
                    ))
                  ) : (
                    <p className="text-sm text-muted-foreground">No trending topics yet</p>
                  )}
                </div>
              </Card>

              <Card className="p-6 border border-border/50">
                <h3 className="text-lg font-semibold mb-4">Recent Insights</h3>
                <div className="space-y-3">
                  {recentInsights.length > 0 ? (
                    recentInsights.map((insight, index) => (
                      <div key={index} className="text-sm">
                        <p className="font-medium">{insight.title}</p>
                    <p className="text-xs text-muted-foreground mt-1">
                          {insight.description}
                    </p>
                  </div>
                    ))
                  ) : (
                    <p className="text-sm text-muted-foreground">No insights available yet</p>
                  )}
                </div>
              </Card>
            </div>
          </div>
        </div>
      </PageContent>
    </AppLayout>
  )
}
