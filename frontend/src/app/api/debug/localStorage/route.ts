import { NextRequest, NextResponse } from 'next/server'

// This is a debug endpoint - would normally be removed in production
export async function GET(request: NextRequest) {
  const url = new URL(request.url)
  const key = url.searchParams.get('key')
  
  // Return instructions for accessing localStorage from browser
  return NextResponse.json({
    message: "localStorage can only be accessed from the browser. Open browser console and run:",
    instructions: key 
      ? `localStorage.getItem('${key}')`
      : "localStorage.getItem('papertrail_memories') or localStorage.getItem('papertrail_conversation')",
    available_keys: [
      'papertrail_memories',
      'papertrail_conversation', 
      'papertrail_conversation_id'
    ]
  })
}