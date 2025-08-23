import { NextResponse } from 'next/server'

export async function GET() {
  try {
    // This route helps debug memory state
    const diagnostic = {
      timestamp: new Date().toISOString(),
      frontend_api_test: null as any,
      backend_api_test: null as any,
      note: "This endpoint helps debug memory system state"
    }
    
    // Test frontend memories API
    try {
      const frontendResponse = await fetch('http://localhost:3000/api/memories')
      diagnostic.frontend_api_test = {
        status: frontendResponse.status,
        ok: frontendResponse.ok,
        data_length: frontendResponse.ok ? (await frontendResponse.json()).length : 'error'
      }
    } catch (err) {
      diagnostic.frontend_api_test = { error: String(err) }
    }
    
    // Test backend memories API
    try {
      const backendResponse = await fetch('http://localhost:8000/api/v1/memories/')
      diagnostic.backend_api_test = {
        status: backendResponse.status,
        ok: backendResponse.ok,
        data_length: backendResponse.ok ? (await backendResponse.json()).length : 'error'
      }
    } catch (err) {
      diagnostic.backend_api_test = { error: String(err) }
    }

    return NextResponse.json(diagnostic)
  } catch (error) {
    return NextResponse.json(
      { error: 'Failed to run diagnostics', details: String(error) },
      { status: 500 }
    )
  }
}