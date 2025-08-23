import { NextResponse } from 'next/server'

export async function POST() {
  try {
    // This is a debug endpoint to help users clear localStorage memories
    // The actual clearing happens on the frontend via localStorage
    
    return NextResponse.json({
      success: true,
      message: "To clear memories, run this in your browser console:",
      commands: [
        "localStorage.removeItem('papertrail_memories')",
        "localStorage.removeItem('papertrail_conversation')", 
        "localStorage.removeItem('papertrail_conversation_id')",
        "window.location.reload()"
      ],
      instruction: "Or use the Clear button on the /debug page"
    })
  } catch (error) {
    return NextResponse.json(
      { error: 'Failed to provide clear instructions' },
      { status: 500 }
    )
  }
}