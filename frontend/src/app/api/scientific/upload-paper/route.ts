import { NextRequest, NextResponse } from 'next/server'
import { writeFile, mkdir } from 'fs/promises'
import { existsSync } from 'fs'
import path from 'path'

const UPLOAD_DIR = path.join(process.cwd(), 'uploads', 'papers')

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData()
    const file = formData.get('file') as File
    const paperId = formData.get('paperId') as string

    if (!file || !paperId) {
      return NextResponse.json(
        { error: 'File and paperId are required' },
        { status: 400 }
      )
    }

    // Ensure upload directory exists
    if (!existsSync(UPLOAD_DIR)) {
      await mkdir(UPLOAD_DIR, { recursive: true })
    }

    // Save file
    const bytes = await file.arrayBuffer()
    const buffer = Buffer.from(bytes)
    const filename = `${paperId}.pdf`
    const filepath = path.join(UPLOAD_DIR, filename)
    
    await writeFile(filepath, buffer)

    // Store paper metadata
    const metadata = {
      id: paperId,
      filename: file.name,
      size: file.size,
      uploadedAt: new Date().toISOString(),
      status: 'uploaded',
      filepath
    }

    // TODO: Store in database instead of memory
    // For now, we'll just return success
    return NextResponse.json({
      success: true,
      paperId,
      metadata,
      message: 'Paper uploaded successfully'
    })

  } catch (error) {
    console.error('Paper upload error:', error)
    return NextResponse.json(
      { error: 'Failed to upload paper' },
      { status: 500 }
    )
  }
}