"use client"

import React from 'react'
import { FileText, MessageSquare, Lightbulb, Network, Upload } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { cn } from '@/lib/utils'

interface Activity {
  id: string
  type: 'paper_uploaded' | 'conversation_started' | 'claim_extracted' | 'graph_updated' | 'paper_processed'
  title: string
  description: string
  timestamp: Date
  metadata?: Record<string, any>
}

interface ActivityFeedProps {
  activities: Activity[]
  maxItems?: number
}

const activityConfig = {
  paper_uploaded: {
    icon: Upload,
    color: 'text-blue-600',
    bgColor: 'bg-blue-500/10',
  },
  conversation_started: {
    icon: MessageSquare,
    color: 'text-green-600',
    bgColor: 'bg-green-500/10',
  },
  claim_extracted: {
    icon: Lightbulb,
    color: 'text-yellow-600',
    bgColor: 'bg-yellow-500/10',
  },
  graph_updated: {
    icon: Network,
    color: 'text-purple-600',
    bgColor: 'bg-purple-500/10',
  },
  paper_processed: {
    icon: FileText,
    color: 'text-indigo-600',
    bgColor: 'bg-indigo-500/10',
  },
}

function formatRelativeTime(date: Date): string {
  const now = new Date()
  const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000)

  if (diffInSeconds < 60) return 'Just now'
  if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`
  if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`
  if (diffInSeconds < 604800) return `${Math.floor(diffInSeconds / 86400)}d ago`
  return date.toLocaleDateString()
}

export function ActivityFeed({ activities, maxItems = 10 }: ActivityFeedProps) {
  const displayedActivities = activities.slice(0, maxItems)

  if (activities.length === 0) {
    return (
      <Card className="p-8 text-center">
        <p className="text-sm text-muted-foreground">No recent activity</p>
        <p className="text-xs text-muted-foreground mt-1">
          Upload a paper or start a conversation to get started
        </p>
      </Card>
    )
  }

  return (
    <Card className="p-6">
      <h3 className="text-lg font-semibold mb-4">Recent Activity</h3>
      <div className="space-y-4">
        {displayedActivities.map((activity, index) => {
          const config = activityConfig[activity.type]
          const Icon = config.icon

          return (
            <div
              key={activity.id}
              className={cn(
                'flex gap-3 pb-4',
                index !== displayedActivities.length - 1 && 'border-b'
              )}
            >
              <div className={cn('p-2 rounded-lg h-fit', config.bgColor)}>
                <Icon className={cn('w-4 h-4', config.color)} />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium leading-tight">{activity.title}</p>
                <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                  {activity.description}
                </p>
                <p className="text-xs text-muted-foreground mt-1.5">
                  {formatRelativeTime(activity.timestamp)}
                </p>
              </div>
            </div>
          )
        })}
      </div>
      {activities.length > maxItems && (
        <button className="text-sm text-primary-600 hover:text-primary-700 font-medium mt-4 w-full text-center">
          View all activity ({activities.length})
        </button>
      )}
    </Card>
  )
}
