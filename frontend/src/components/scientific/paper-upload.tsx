"use client"

import React, { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Progress } from '@/components/ui/progress'
import { 
  Upload, 
  FileText, 
  Link, 
  AlertCircle, 
  CheckCircle,
  Loader2,
  X
} from 'lucide-react'

interface PaperUploadProps {
  onPaperUploaded: (paperId: string, metadata: any) => void
  className?: string
}

interface UploadedPaper {
  id: string
  title?: string
  authors?: string[]
  status: 'uploading' | 'parsing' | 'extracting' | 'complete' | 'error'
  progress: number
  error?: string
}

const PaperUpload = ({ onPaperUploaded, className }: PaperUploadProps) => {
  const [papers, setPapers] = useState<UploadedPaper[]>([])
  const [doiInput, setDoiInput] = useState('')
  const [arxivInput, setArxivInput] = useState('')

  // Handle file uploads
  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    for (const file of acceptedFiles) {
      const paperId = `paper_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
      
      // Add paper to tracking list
      const newPaper: UploadedPaper = {
        id: paperId,
        title: file.name,
        status: 'uploading',
        progress: 0
      }
      
      setPapers(prev => [...prev, newPaper])
      
      try {
        // Create form data for upload
        const formData = new FormData()
        formData.append('file', file)
        formData.append('paperId', paperId)
        
        // Upload and parse paper
        await uploadAndParsePaper(formData, paperId)
        
      } catch (error) {
        setPapers(prev => prev.map(p => 
          p.id === paperId 
            ? { ...p, status: 'error', error: 'Upload failed: ' + String(error) }
            : p
        ))
      }
    }
  }, [])

  const uploadAndParsePaper = async (formData: FormData, paperId: string) => {
    // Stage 1: Upload
    setPapers(prev => prev.map(p => 
      p.id === paperId ? { ...p, status: 'uploading', progress: 25 } : p
    ))
    
    const uploadResponse = await fetch('/api/scientific/upload-paper', {
      method: 'POST',
      body: formData
    })
    
    if (!uploadResponse.ok) {
      throw new Error('Upload failed')
    }
    
    // Stage 2: Parse with Grobid
    setPapers(prev => prev.map(p => 
      p.id === paperId ? { ...p, status: 'parsing', progress: 50 } : p
    ))
    
    const parseResponse = await fetch('/api/scientific/parse-paper', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ paperId })
    })
    
    if (!parseResponse.ok) {
      throw new Error('Parsing failed')
    }
    
    const parseData = await parseResponse.json()
    
    // Stage 3: Extract claims and build graph
    setPapers(prev => prev.map(p => 
      p.id === paperId ? { 
        ...p, 
        status: 'extracting', 
        progress: 75,
        title: parseData.title,
        authors: parseData.authors
      } : p
    ))
    
    const extractResponse = await fetch('/api/scientific/extract-claims', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ paperId })
    })
    
    if (!extractResponse.ok) {
      throw new Error('Claim extraction failed')
    }
    
    const extractData = await extractResponse.json()
    
    // Complete
    setPapers(prev => prev.map(p => 
      p.id === paperId ? { ...p, status: 'complete', progress: 100 } : p
    ))
    
    onPaperUploaded(paperId, {
      ...parseData,
      claims: extractData.claims,
      entities: extractData.entities
    })
  }

  const handleDoiSubmit = async () => {
    if (!doiInput.trim()) return
    
    const paperId = `doi_${Date.now()}`
    const newPaper: UploadedPaper = {
      id: paperId,
      title: `DOI: ${doiInput}`,
      status: 'uploading',
      progress: 0
    }
    
    setPapers(prev => [...prev, newPaper])
    
    try {
      const response = await fetch('/api/scientific/fetch-doi', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ doi: doiInput })
      })
      
      if (!response.ok) throw new Error('DOI fetch failed')
      
      // Follow same parsing pipeline as file upload
      await uploadAndParsePaper(new FormData(), paperId)
      setDoiInput('')
      
    } catch (error) {
      setPapers(prev => prev.map(p => 
        p.id === paperId 
          ? { ...p, status: 'error', error: String(error) }
          : p
      ))
    }
  }

  const handleArxivSubmit = async () => {
    if (!arxivInput.trim()) return
    
    const paperId = `arxiv_${Date.now()}`
    const newPaper: UploadedPaper = {
      id: paperId,
      title: `arXiv: ${arxivInput}`,
      status: 'uploading',
      progress: 0
    }
    
    setPapers(prev => [...prev, newPaper])
    
    try {
      const response = await fetch('/api/scientific/fetch-arxiv', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ arxivId: arxivInput })
      })
      
      if (!response.ok) throw new Error('arXiv fetch failed')
      
      await uploadAndParsePaper(new FormData(), paperId)
      setArxivInput('')
      
    } catch (error) {
      setPapers(prev => prev.map(p => 
        p.id === paperId 
          ? { ...p, status: 'error', error: String(error) }
          : p
      ))
    }
  }

  const removePaper = (paperId: string) => {
    setPapers(prev => prev.filter(p => p.id !== paperId))
  }

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf']
    },
    maxSize: 50 * 1024 * 1024, // 50MB
    multiple: true
  })

  const getStatusIcon = (status: UploadedPaper['status']) => {
    switch (status) {
      case 'uploading':
      case 'parsing':
      case 'extracting':
        return <Loader2 className="w-4 h-4 animate-spin text-blue-500" />
      case 'complete':
        return <CheckCircle className="w-4 h-4 text-green-500" />
      case 'error':
        return <AlertCircle className="w-4 h-4 text-red-500" />
    }
  }

  const getStatusText = (status: UploadedPaper['status']) => {
    switch (status) {
      case 'uploading': return 'Uploading...'
      case 'parsing': return 'Parsing PDF...'
      case 'extracting': return 'Extracting claims...'
      case 'complete': return 'Ready for analysis'
      case 'error': return 'Failed'
    }
  }

  return (
    <div className={`space-y-6 ${className}`}>
      {/* File Upload Area */}
      <Card className="p-6">
        <h2 className="text-lg font-semibold mb-4">Upload Research Papers</h2>
        
        <div 
          {...getRootProps()} 
          className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
            isDragActive 
              ? 'border-blue-500 bg-blue-50' 
              : 'border-gray-300 hover:border-gray-400'
          }`}
        >
          <input {...getInputProps()} />
          <Upload className="w-12 h-12 mx-auto text-gray-400 mb-4" />
          {isDragActive ? (
            <p className="text-blue-600">Drop PDF files here...</p>
          ) : (
            <div>
              <p className="text-gray-600 mb-2">
                Drag & drop PDF files here, or click to browse
              </p>
              <p className="text-sm text-gray-400">
                Supports multiple files up to 50MB each
              </p>
            </div>
          )}
        </div>
      </Card>

      {/* DOI and arXiv Input */}
      <div className="grid md:grid-cols-2 gap-4">
        <Card className="p-4">
          <h3 className="font-medium mb-3 flex items-center gap-2">
            <Link className="w-4 h-4" />
            Fetch by DOI
          </h3>
          <div className="flex gap-2">
            <Input
              placeholder="10.1000/182"
              value={doiInput}
              onChange={(e) => setDoiInput(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleDoiSubmit()}
            />
            <Button onClick={handleDoiSubmit} disabled={!doiInput.trim()}>
              Fetch
            </Button>
          </div>
        </Card>

        <Card className="p-4">
          <h3 className="font-medium mb-3 flex items-center gap-2">
            <FileText className="w-4 h-4" />
            Fetch from arXiv
          </h3>
          <div className="flex gap-2">
            <Input
              placeholder="2301.08727"
              value={arxivInput}
              onChange={(e) => setArxivInput(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleArxivSubmit()}
            />
            <Button onClick={handleArxivSubmit} disabled={!arxivInput.trim()}>
              Fetch
            </Button>
          </div>
        </Card>
      </div>

      {/* Processing Status */}
      {papers.length > 0 && (
        <Card className="p-4">
          <h3 className="font-medium mb-4">Paper Processing Status</h3>
          <div className="space-y-3">
            {papers.map(paper => (
              <div key={paper.id} className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                {getStatusIcon(paper.status)}
                
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <h4 className="font-medium text-sm truncate">
                      {paper.title}
                    </h4>
                    {paper.authors && (
                      <span className="text-xs text-gray-500">
                        by {paper.authors.slice(0, 2).join(', ')}
                        {paper.authors.length > 2 && ` +${paper.authors.length - 2}`}
                      </span>
                    )}
                  </div>
                  
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-xs text-gray-600">
                      {getStatusText(paper.status)}
                    </span>
                    {paper.error && (
                      <span className="text-xs text-red-600">
                        {paper.error}
                      </span>
                    )}
                  </div>
                  
                  {paper.status !== 'error' && paper.status !== 'complete' && (
                    <Progress value={paper.progress} className="h-1 mt-2" />
                  )}
                </div>
                
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => removePaper(paper.id)}
                >
                  <X className="w-4 h-4" />
                </Button>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  )
}

export default PaperUpload