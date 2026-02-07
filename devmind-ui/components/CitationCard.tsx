'use client'

import { Card } from '@/components/ui/card'
import { FileCode, ExternalLink } from 'lucide-react'

interface CitationCardProps {
  citation: {
    id: number
    file_path: string
    start_line: number
    end_line: number
    score: number
    section_type?: string
  }
}

export function CitationCard({ citation }: CitationCardProps) {
  return (
    <Card className="p-3 hover:border-primary transition-colors cursor-pointer">
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-start gap-2 flex-1 min-w-0">
          <FileCode className="w-4 h-4 mt-0.5 flex-shrink-0 text-primary" />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-mono truncate">{citation.file_path}</p>
            <div className="flex items-center gap-2 text-xs text-muted-foreground mt-1">
              <span>Lines {citation.start_line}-{citation.end_line}</span>
              {citation.section_type && (
                <>
                  <span>•</span>
                  <span className="capitalize">{citation.section_type}</span>
                </>
              )}
              <span>•</span>
              <span>Score: {citation.score.toFixed(2)}</span>
            </div>
          </div>
        </div>
        <ExternalLink className="w-4 h-4 flex-shrink-0 text-muted-foreground" />
      </div>
    </Card>
  )
}
