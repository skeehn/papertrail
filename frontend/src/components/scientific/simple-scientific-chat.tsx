"use client"

import React, { useEffect, useRef, useState } from 'react'
import { useChat } from '@ai-sdk/react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Card } from '@/components/ui/card'
import { Brain, Upload, RotateCcw, Send, FileText, X } from 'lucide-react'

export default function SimpleScientificChat() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [uploadStatus, setUploadStatus] = useState<'idle' | 'uploading' | 'success' | 'error'>('idle')
  const [uploadProgress, setUploadProgress] = useState(0)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [processingId, setProcessingId] = useState<string | null>(null)
  const [processingStatus, setProcessingStatus] = useState<string | null>(null)
  const [processingMessage, setProcessingMessage] = useState<string | null>(null)
  const uploadAbortRef = useRef<AbortController | null>(null)
  const fileInputRef = useRef<HTMLInputElement | null>(null)
  
  const chat = useChat()
  const { messages } = chat
  const input = (chat as any).input as string | undefined
  const handleInputChange = (chat as any).handleInputChange as ((e: any) => void) | undefined
  const handleSubmit = (chat as any).handleSubmit as ((e: any) => void) | undefined
  const isLoading = (chat as any).isLoading as boolean | undefined

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (input?.trim() && !isLoading && handleSubmit) {
      handleSubmit(e)
    }
  }

  const resetUploadState = () => {
    setSelectedFile(null)
    setUploadStatus('idle')
    setUploadProgress(0)
    setUploadError(null)
    setProcessingId(null)
    setProcessingStatus(null)
    setProcessingMessage(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) {
      resetUploadState()
      return
    }

    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setUploadStatus('error')
      setUploadError('Only PDF files are supported. Please select a PDF document.')
      setSelectedFile(null)
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
      return
    }

    setSelectedFile(file)
    setUploadStatus('idle')
    setUploadProgress(0)
    setUploadError(null)
    setProcessingId(null)
    setProcessingStatus(null)
    setProcessingMessage(null)
  }

  const handleUpload = async () => {
    if (!selectedFile) {
      return
    }

    const abortController = new AbortController()
    uploadAbortRef.current = abortController

    setUploadStatus('uploading')
    setUploadProgress(0)
    setUploadError(null)
    setProcessingId(null)
    setProcessingStatus(null)
    setProcessingMessage('Starting upload...')

    try {
      const formData = new FormData()
      formData.append('file', selectedFile)

      setUploadProgress(25)

      const response = await fetch('/api/v1/papers/upload', {
        method: 'POST',
        body: formData,
        signal: abortController.signal,
      })

      let data: any = null
      try {
        data = await response.json()
      } catch {
        // Ignore JSON parse errors; we'll fall back to status text below.
      }

      if (!response.ok) {
        const errorMessage =
          data?.detail ||
          data?.error ||
          response.statusText ||
          'Failed to upload the PDF. Please try again.'
        throw new Error(errorMessage)
      }

      if (!data) {
        throw new Error('Unexpected response from the server. Please try again later.')
      }

      const processingIdentifier = (data.processing_id as string | undefined) ?? null
      const initialStatus = (data.status as string | undefined) ?? null

      setUploadProgress(100)
      setUploadStatus('success')
      setProcessingId(processingIdentifier)
      setProcessingStatus(initialStatus)
      setProcessingMessage(
        processingIdentifier
          ? 'Paper uploaded successfully. We will notify you when processing finishes.'
          : 'Paper uploaded successfully. Waiting for processing to begin...'
      )
    } catch (error) {
      if ((error as Error).name === 'AbortError') {
        setProcessingMessage('Upload cancelled.')
        setUploadStatus('idle')
        setUploadProgress(0)
        setProcessingId(null)
        setProcessingStatus(null)
      } else {
        setUploadStatus('error')
        setUploadError(
          (error as Error).message || 'Something went wrong while uploading the paper.'
        )
        setUploadProgress(0)
        setProcessingMessage(null)
        setProcessingId(null)
        setProcessingStatus(null)
      }
    } finally {
      uploadAbortRef.current = null
    }
  }

  const handleCancelUpload = () => {
    if (uploadAbortRef.current) {
      uploadAbortRef.current.abort()
    }
  }

  useEffect(() => {
    if (!processingId) {
      return
    }

    let isActive = true
    const pollInterval = 5000
    let intervalId: ReturnType<typeof setInterval> | null = null

    const pollProcessingStatus = async () => {
      try {
        const response = await fetch(`/api/v1/papers/${processingId}`)
        if (!isActive) {
          return
        }

        if (!response.ok) {
          if (response.status === 404) {
            setProcessingMessage('Processing has started. Waiting for status updates...')
          }
          return
        }

        const data = await response.json()
        const status = (data.status as string | undefined) ?? null

        if (status) {
          setProcessingStatus(status)

          if (status === 'completed') {
            setProcessingMessage('Processing completed! You can now chat about this paper.')
            isActive = false
            if (intervalId) {
              clearInterval(intervalId)
            }
          } else if (status === 'failed') {
            setProcessingMessage('Processing failed. Please try uploading the paper again.')
            isActive = false
            if (intervalId) {
              clearInterval(intervalId)
            }
          } else if (status === 'processing') {
            setProcessingMessage('The paper is being processed...')
          } else if (status === 'pending') {
            setProcessingMessage('Paper received. Processing will begin shortly...')
          }
        }
      } catch {
        if (isActive) {
          setProcessingMessage('Waiting for processing updates...')
        }
      }
    }

    pollProcessingStatus()
    intervalId = setInterval(() => {
      if (isActive) {
        pollProcessingStatus()
      }
    }, pollInterval)

    return () => {
      isActive = false
      if (intervalId) {
        clearInterval(intervalId)
      }
    }
  }, [processingId])

  return (
    <div className="flex flex-col h-screen bg-white">
      <input
        ref={fileInputRef}
        type="file"
        accept="application/pdf"
        onChange={handleFileChange}
        className="hidden"
      />
      {/* Header */}
      <div className="border-b bg-gray-50 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Brain className="w-6 h-6 text-blue-500" />
            <h1 className="text-xl font-semibold">PaperTrail 2.0</h1>
          </div>
          <div className="flex gap-2">
            <Button
              onClick={() => {
                if (uploadStatus !== 'uploading') {
                  fileInputRef.current?.click()
                }
              }}
              variant="outline"
              size="sm"
              className="flex items-center gap-2"
              disabled={uploadStatus === 'uploading'}
            >
              <Upload className="w-4 h-4" />
              Add PDF
            </Button>
            <Button
              onClick={() => window.location.reload()}
              variant="outline"
              size="sm"
              className="flex items-center gap-2"
            >
              <RotateCcw className="w-4 h-4" />
              Clear
            </Button>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-4xl mx-auto space-y-6">
          {messages.length === 0 && (
            <Card className="p-6 text-center">
              <Brain className="w-12 h-12 text-blue-500 mx-auto mb-4" />
              <h2 className="text-xl font-semibold mb-2">Welcome to PaperTrail 2.0!</h2>
              <p className="text-gray-600 mb-6">
                I&apos;m your intelligent research assistant. I can help you analyze scientific literature, 
                map arguments, and discover research insights.
              </p>
              <div className="text-left bg-gray-50 p-4 rounded-lg">
                <p className="text-sm font-medium text-gray-700 mb-2">Try asking me:</p>
                <ul className="text-sm text-gray-600 space-y-1">
                  <li>• &quot;What papers do I have about machine learning?&quot;</li>
                  <li>• &quot;Find research on neural networks&quot;</li>
                  <li>• &quot;Show me claims about AI accuracy improvements&quot;</li>
                  <li>• &quot;Are there contradictions in my research collection?&quot;</li>
                </ul>
              </div>
            </Card>
          )}

          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex gap-3 ${
                message.role === 'user' ? 'justify-end' : 'justify-start'
              }`}
            >
              {message.role === 'assistant' && (
                <div className="w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center text-white text-sm font-medium">
                  AI
                </div>
              )}
              <div
                className={`max-w-3xl p-4 rounded-lg ${
                  message.role === 'user'
                    ? 'bg-blue-500 text-white'
                    : 'bg-gray-100 text-gray-900'
                }`}
              >
                <div className="prose prose-sm max-w-none">
                  {Array.isArray((message as any).parts)
                    ? (message as any).parts
                        .filter((p: any) => p && (typeof p === 'string' || p.type === 'text'))
                        .map((p: any) => (typeof p === 'string' ? p : p.text))
                        .join('')
                    : (message as any).content ?? ''}
                </div>
              </div>
              {message.role === 'user' && (
                <div className="w-8 h-8 bg-gray-500 rounded-full flex items-center justify-center text-white text-sm font-medium">
                  {messages.length > 1 ? 'S' : 'U'}
                </div>
              )}
            </div>
          ))}

          {isLoading && (
            <div className="flex gap-3 justify-start">
              <div className="w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center text-white text-sm font-medium">
                AI
              </div>
              <div className="max-w-3xl p-4 rounded-lg bg-gray-100">
                <div className="flex items-center gap-2">
                  <div className="animate-spin w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full"></div>
                  <span className="text-gray-600">Thinking...</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Input */}
      <div className="border-t bg-white p-6 space-y-4">
        <form onSubmit={onSubmit} className="max-w-4xl mx-auto space-y-3">
          <div className="flex items-start gap-3">
            <Textarea
              value={input}
              onChange={handleInputChange}
              placeholder="Ask about research papers, upload documents, or explore scientific topics..."
              className="flex-1 min-h-[50px] resize-none"
              rows={2}
            />
            <div className="flex flex-col gap-2">
              <Button
                type="button"
                variant="outline"
                className="flex items-center gap-2"
                onClick={() => {
                  if (uploadStatus !== 'uploading') {
                    fileInputRef.current?.click()
                  }
                }}
                disabled={uploadStatus === 'uploading'}
              >
                <Upload className="w-4 h-4" />
                Attach
              </Button>
              <Button
                type="submit"
                disabled={!input?.trim() || isLoading}
                className="px-6 flex items-center gap-2"
              >
                <Send className="w-4 h-4" />
                Send
              </Button>
            </div>
          </div>
          <p className="text-xs text-gray-500 text-center">
            I can search your papers, analyze claims, and provide research insights.
          </p>
        </form>

        {(selectedFile || uploadStatus !== 'idle' || processingId || uploadError) && (
          <div className="max-w-4xl mx-auto">
            <Card className="p-4 space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-2 text-sm text-gray-700">
                  <FileText className="w-4 h-4 text-blue-500" />
                  <div className="flex flex-col">
                    <span className="font-medium">
                      {selectedFile ? selectedFile.name : 'No file selected'}
                    </span>
                    {selectedFile && (
                      <span className="text-xs text-gray-500">
                        {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB
                      </span>
                    )}
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  {uploadStatus !== 'uploading' && selectedFile && (
                    <Button
                      onClick={handleUpload}
                      disabled={!selectedFile}
                      className="flex items-center gap-2"
                    >
                      <Upload className="w-4 h-4" />
                      Upload &amp; Process
                    </Button>
                  )}

                  {uploadStatus === 'uploading' && (
                    <Button variant="outline" onClick={handleCancelUpload}>
                      Cancel Upload
                    </Button>
                  )}

                  {(selectedFile || uploadStatus !== 'idle' || processingId) && (
                    <Button variant="ghost" onClick={resetUploadState} className="flex items-center gap-2">
                      <X className="w-4 h-4" />
                      Clear
                    </Button>
                  )}
                </div>
              </div>

              {(uploadStatus === 'uploading' || uploadProgress > 0) && (
                <div className="space-y-2">
                  <div className="h-2 w-full bg-gray-200 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-blue-500 transition-all duration-500"
                      style={{ width: `${uploadProgress}%` }}
                    ></div>
                  </div>
                  <p className="text-xs text-gray-500">
                    {uploadStatus === 'uploading'
                      ? `Uploading... ${Math.round(uploadProgress)}%`
                      : uploadStatus === 'success'
                        ? 'Upload complete! Monitoring processing status.'
                        : 'Ready to upload your PDF.'}
                  </p>
                </div>
              )}

              {uploadStatus === 'error' && uploadError && (
                <p className="text-sm text-red-500">{uploadError}</p>
              )}

              {processingId && (
                <div className="rounded-lg border border-dashed border-blue-200 bg-blue-50 p-4 text-sm text-blue-900">
                  <p className="font-medium">Processing ID: {processingId}</p>
                  {processingStatus && <p className="mt-1">Current status: {processingStatus}</p>}
                  {processingMessage && (
                    <p className="mt-2 text-xs text-blue-700">{processingMessage}</p>
                  )}
                </div>
              )}

              {uploadStatus === 'success' && !processingId && processingMessage && (
                <p className="text-sm text-blue-600">{processingMessage}</p>
              )}
            </Card>
          </div>
        )}
      </div>
    </div>
  )
}