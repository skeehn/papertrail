"use client"

import React, { useState } from 'react'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { 
  Brain,
  CheckCircle,
  AlertTriangle,
  Search,
  Filter,
  Quote,
  ExternalLink
} from 'lucide-react'

interface ClaimsListProps {
  papers: any[]
  selectedPaper: any
}

const ClaimsList = ({ papers, selectedPaper }: ClaimsListProps) => {
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedConfidenceFilter, setSelectedConfidenceFilter] = useState<'all' | 'high' | 'medium' | 'low'>('all')
  const [selectedModalityFilter, setSelectedModalityFilter] = useState<'all' | 'strong' | 'weak' | 'speculative'>('all')

  if (!selectedPaper || !selectedPaper.claims) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <Brain className="w-12 h-12 mx-auto text-gray-300 mb-4" />
          <h3 className="font-medium text-gray-900 mb-2">No Claims Available</h3>
          <p className="text-sm text-gray-600">
            Select a paper with extracted claims to view analysis
          </p>
        </div>
      </div>
    )
  }

  const filteredClaims = selectedPaper.claims.filter((claim: any) => {
    // Search filter
    const matchesSearch = claim.text.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         claim.subject.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         claim.object.toLowerCase().includes(searchTerm.toLowerCase())

    // Confidence filter
    let matchesConfidence = true
    if (selectedConfidenceFilter !== 'all') {
      const confidence = claim.confidence
      if (selectedConfidenceFilter === 'high') matchesConfidence = confidence >= 0.8
      else if (selectedConfidenceFilter === 'medium') matchesConfidence = confidence >= 0.5 && confidence < 0.8
      else if (selectedConfidenceFilter === 'low') matchesConfidence = confidence < 0.5
    }

    // Modality filter
    const matchesModality = selectedModalityFilter === 'all' || claim.modality === selectedModalityFilter

    return matchesSearch && matchesConfidence && matchesModality
  })

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'text-green-600 bg-green-100'
    if (confidence >= 0.5) return 'text-yellow-600 bg-yellow-100'
    return 'text-red-600 bg-red-100'
  }

  const getModalityIcon = (modality: string) => {
    switch (modality) {
      case 'strong': return <CheckCircle className="w-4 h-4 text-green-500" />
      case 'weak': return <AlertTriangle className="w-4 h-4 text-yellow-500" />
      case 'speculative': return <AlertTriangle className="w-4 h-4 text-orange-500" />
      default: return <Brain className="w-4 h-4 text-gray-500" />
    }
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header with filters */}
      <div className="border-b p-4 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold">Claims Analysis</h3>
          <Badge variant="outline">
            {filteredClaims.length} of {selectedPaper.claims.length} claims
          </Badge>
        </div>

        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
          <Input
            placeholder="Search claims, subjects, objects..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-9"
          />
        </div>

        {/* Filters */}
        <div className="flex flex-wrap gap-2">
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-gray-500" />
            <span className="text-xs text-gray-500">Confidence:</span>
            {(['all', 'high', 'medium', 'low'] as const).map(level => (
              <Button
                key={level}
                variant={selectedConfidenceFilter === level ? 'default' : 'outline'}
                size="sm"
                onClick={() => setSelectedConfidenceFilter(level)}
                className="text-xs h-6"
              >
                {level}
              </Button>
            ))}
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          <span className="text-xs text-gray-500">Modality:</span>
          {(['all', 'strong', 'weak', 'speculative'] as const).map(modality => (
            <Button
              key={modality}
              variant={selectedModalityFilter === modality ? 'default' : 'outline'}
              size="sm"
              onClick={() => setSelectedModalityFilter(modality)}
              className="text-xs h-6"
            >
              {modality}
            </Button>
          ))}
        </div>
      </div>

      {/* Claims list */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {filteredClaims.map((claim: any, index: number) => (
          <Card key={claim.id} className="p-4 hover:shadow-md transition-shadow">
            <div className="space-y-3">
              {/* Claim header */}
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-2">
                  {getModalityIcon(claim.modality)}
                  <Badge variant="outline" className="text-xs">
                    {claim.modality}
                  </Badge>
                  <Badge className={`text-xs ${getConfidenceColor(claim.confidence)}`}>
                    {Math.round(claim.confidence * 100)}%
                  </Badge>
                </div>
                
                <Badge variant="secondary" className="text-xs">
                  {claim.section}
                </Badge>
              </div>

              {/* Main claim text */}
              <div className="space-y-2">
                <div className="flex items-start gap-2">
                  <Quote className="w-4 h-4 text-gray-400 mt-0.5 flex-shrink-0" />
                  <p className="text-sm font-medium text-gray-900">
                    {claim.text}
                  </p>
                </div>
              </div>

              {/* Structured claim components */}
              <div className="grid grid-cols-3 gap-3 text-xs">
                <div>
                  <span className="text-gray-500 block mb-1">Subject:</span>
                  <span className="font-medium">{claim.subject}</span>
                </div>
                <div>
                  <span className="text-gray-500 block mb-1">Predicate:</span>
                  <span className="font-medium">{claim.predicate}</span>
                </div>
                <div>
                  <span className="text-gray-500 block mb-1">Object:</span>
                  <span className="font-medium">{claim.object}</span>
                </div>
              </div>

              {/* Evidence span */}
              {claim.evidence_span && (
                <div className="bg-gray-50 p-3 rounded-lg">
                  <span className="text-xs text-gray-500 block mb-1">Evidence:</span>
                  <p className="text-xs text-gray-700 italic">
                    &quot;{claim.evidence_span}&quot;
                  </p>
                </div>
              )}

              {/* Supporting citations */}
              {claim.supporting_citations && claim.supporting_citations.length > 0 && (
                <div className="flex items-center gap-2">
                  <ExternalLink className="w-3 h-3 text-gray-400" />
                  <span className="text-xs text-gray-500">
                    {claim.supporting_citations.length} supporting citation{claim.supporting_citations.length !== 1 ? 's' : ''}
                  </span>
                  <div className="flex gap-1">
                    {claim.supporting_citations.slice(0, 3).map((citation: string, idx: number) => (
                      <Badge key={idx} variant="outline" className="text-xs">
                        {citation}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </Card>
        ))}

        {filteredClaims.length === 0 && (
          <div className="text-center py-8">
            <Search className="w-8 h-8 mx-auto text-gray-300 mb-3" />
            <p className="text-sm text-gray-500">
              No claims match your current filters
            </p>
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setSearchTerm('')
                setSelectedConfidenceFilter('all')
                setSelectedModalityFilter('all')
              }}
              className="mt-2"
            >
              Clear filters
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}

export default ClaimsList